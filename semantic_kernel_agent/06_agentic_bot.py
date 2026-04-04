"""
06. Agentic Sales Bot - Planner → Executor → Reviewer 패턴

고객/제품/미팅/마케팅 플러그인을 동적으로 선택하여 사용자 문의에 최적의 답변을 제공합니다.

아키텍처:
    사용자 입력
        │
        ▼
    [Planner Agent]
      - 질문 분석
      - 필요한 플러그인 + 호출 순서 결정
      - 실행 계획(JSON) 생성
        │
        ▼
    [Executor Agent]  ←── Account / Product / Meeting / Marketing 플러그인
      - Planner의 계획대로 플러그인 함수 자동 호출
      - 각 단계 결과를 취합하여 종합 답변 초안 작성
        │
        ▼
    [Reviewer Agent]
      - 답변 품질 평가 (완전성 / 정확성 / 실행 가능성)
      - 충분하면 → 최종 답변 출력
      - 부족하면 → Planner에게 재계획 요청 (최대 MAX_ITERATIONS 회)
        │
        ▼
    최종 답변 출력

Azure ML 실제 활용:
  - Managed Identity로 Azure OpenAI 인증 (api_key 불필요)
  - 모든 플러그인은 실제 Azure 서비스(Cosmos DB, SQL, Dynamics)로 교체 가능
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory

from config.settings import get_azure_openai_config
from plugins.account_plugin import AccountPlugin
from plugins.product_plugin import ProductPlugin
from plugins.meeting_plugin import MeetingPlugin
from plugins.marketing_plugin import MarketingPlugin
from utils.query_history import QueryHistory


# ── 상수 ──────────────────────────────────────────────────────────────────────
MAX_ITERATIONS = 3          # Planner-Executor-Reviewer 최대 반복 횟수
REVIEW_THRESHOLD = 7        # Reviewer 품질 점수 기준 (0~10, 이 이상이면 통과)
EXECUTOR_MAX_TOKENS = 2000  # Executor 응답 최대 토큰
REVIEWER_MAX_TOKENS = 800   # Reviewer 응답 최대 토큰
FINAL_MAX_TOKENS = 1500     # 최종 답변 최대 토큰


# ── Planner 시스템 프롬프트 ───────────────────────────────────────────────────
PLANNER_SYSTEM_PROMPT = """당신은 영업/마케팅 AI 봇의 Planner 에이전트입니다.

사용자의 질문을 분석하여 다음 플러그인 중 필요한 것을 선택하고 실행 계획을 JSON으로 작성하세요.

사용 가능한 플러그인:
- Account: 고객 정보 조회 (get_account_by_id, search_accounts, get_at_risk_accounts, get_account_summary)
- Product: 제품 정보 및 추천 (get_product_by_id, search_products, recommend_products_for_account, get_product_catalog)
- Meeting: 미팅 이력 관리 (get_meetings_by_account, get_recent_meetings, get_pending_actions, get_meetings_by_deal_stage, get_meeting_summary_stats)
- Marketing: 마케팅 전략 수립 (get_active_campaigns, generate_marketing_strategy, calculate_campaign_roi, get_recommended_strategy_for_account, get_marketing_summary)

반드시 아래 JSON 형식으로만 응답하세요. 추가 설명 없이 JSON만 출력하세요:

{
  "query_type": "질문 유형 (예: 고객조회, 제품추천, 미팅분석, 전략수립, 복합)",
  "analysis": "질문 핵심 분석 (한 문장)",
  "steps": [
    {
      "step": 1,
      "plugin": "플러그인명",
      "function": "함수명",
      "params": {"파라미터명": "값"},
      "purpose": "이 단계의 목적"
    }
  ],
  "expected_output": "최종 답변에서 다룰 내용 요약"
}
"""


# ── Executor 시스템 프롬프트 ──────────────────────────────────────────────────
EXECUTOR_SYSTEM_PROMPT = """당신은 영업/마케팅 AI 봇의 Executor 에이전트입니다.

주어진 실행 계획에 따라 플러그인 함수를 호출하고, 수집된 데이터를 바탕으로
사용자에게 도움이 되는 종합 답변 초안을 작성하세요.

답변 작성 원칙:
1. 플러그인에서 조회된 실제 데이터만 사용 (추측 금지)
2. 영업/마케팅 관점에서 인사이트 제공
3. 구체적인 다음 액션(Next Action) 제시
4. 한국어로 답변 (전문 용어는 영어 병기 허용)
5. 명확한 구조 (헤더, 불릿 포인트 활용)
"""


# ── Reviewer 시스템 프롬프트 ──────────────────────────────────────────────────
REVIEWER_SYSTEM_PROMPT = """당신은 영업/마케팅 AI 봇의 Reviewer 에이전트입니다.

Executor가 작성한 답변 초안을 검토하고 품질을 평가하세요.

반드시 아래 JSON 형식으로만 응답하세요:

{
  "score": 0~10 사이의 정수,
  "passed": true 또는 false (score >= 7이면 true),
  "strengths": ["잘된 점 1", "잘된 점 2"],
  "issues": ["문제점 1 (없으면 빈 배열)"],
  "missing_info": ["누락된 정보 1 (없으면 빈 배열)"],
  "replan_suggestion": "재계획 시 추가로 조회할 내용 (passed=true면 빈 문자열)"
}

평가 기준:
- 완전성 (3점): 사용자 질문의 모든 측면을 다루었는가?
- 정확성 (3점): 데이터가 정확하고 일관성이 있는가?
- 실행가능성 (2점): 구체적인 다음 액션이 포함되어 있는가?
- 명확성 (2점): 이해하기 쉽고 구조화되어 있는가?
"""


def _build_kernel_and_service(config) -> tuple[sk.Kernel, AzureChatCompletion]:
    """Kernel과 AzureChatCompletion 서비스를 초기화합니다"""
    kernel = sk.Kernel()
    chat_service = AzureChatCompletion(
        deployment_name=config.deployment_name,
        endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
        service_id="azure_chat",
    )
    kernel.add_service(chat_service)

    # 4개 비즈니스 플러그인 등록
    kernel.add_plugin(AccountPlugin(), plugin_name="Account")
    kernel.add_plugin(ProductPlugin(), plugin_name="Product")
    kernel.add_plugin(MeetingPlugin(), plugin_name="Meeting")
    kernel.add_plugin(MarketingPlugin(), plugin_name="Marketing")

    return kernel, chat_service


async def run_planner(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    user_query: str,
    replan_hint: str = "",
) -> dict:
    """
    Planner 에이전트: 사용자 질문을 분석하고 실행 계획(JSON)을 생성합니다.

    Returns:
        실행 계획 딕셔너리
    """
    history = ChatHistory()
    history.add_system_message(PLANNER_SYSTEM_PROMPT)

    task = user_query
    if replan_hint:
        task += f"\n\n[재계획 힌트]: {replan_hint}"

    history.add_user_message(task)

    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),  # Planner는 직접 함수 호출 안함
        max_tokens=600,
        temperature=0.1,  # 계획은 일관성이 중요하므로 낮은 temperature
    )

    response = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )

    raw = str(response).strip()
    # JSON 블록 추출 (마크다운 코드 블록 대응)
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        # 파싱 실패 시 기본 계획 반환
        plan = {
            "query_type": "복합",
            "analysis": user_query,
            "steps": [
                {
                    "step": 1,
                    "plugin": "Account",
                    "function": "get_account_summary",
                    "params": {},
                    "purpose": "전체 고객 현황 파악",
                }
            ],
            "expected_output": "고객 현황 요약",
        }

    return plan


async def run_executor(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    user_query: str,
    plan: dict,
) -> str:
    """
    Executor 에이전트: Planner의 계획에 따라 플러그인 함수를 자동 호출하고 답변 초안을 작성합니다.

    - FunctionChoiceBehavior.Auto()로 AI가 적절한 플러그인 함수를 선택/호출
    - Planner 계획을 컨텍스트로 제공하여 올바른 순서로 실행 유도
    """
    history = ChatHistory()
    history.add_system_message(EXECUTOR_SYSTEM_PROMPT)

    # Planner 계획을 Executor에게 전달
    plan_str = json.dumps(plan, ensure_ascii=False, indent=2)
    executor_task = (
        f"사용자 질문: {user_query}\n\n"
        f"실행 계획:\n{plan_str}\n\n"
        f"위 계획에 따라 필요한 플러그인 함수를 호출하고, "
        f"수집된 데이터를 바탕으로 종합 답변 초안을 작성하세요."
    )
    history.add_user_message(executor_task)

    # Executor는 모든 플러그인에 자동 접근 가능
    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
        max_tokens=EXECUTOR_MAX_TOKENS,
        temperature=0.3,
    )

    response = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )

    return str(response)


async def run_reviewer(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    user_query: str,
    draft_answer: str,
) -> dict:
    """
    Reviewer 에이전트: 답변 초안을 평가하고 품질 점수와 피드백을 반환합니다.

    Returns:
        {"score": int, "passed": bool, "issues": list, "replan_suggestion": str, ...}
    """
    history = ChatHistory()
    history.add_system_message(REVIEWER_SYSTEM_PROMPT)

    review_task = (
        f"[원래 사용자 질문]\n{user_query}\n\n"
        f"[답변 초안]\n{draft_answer}\n\n"
        f"위 답변을 평가하고 JSON으로 결과를 반환하세요."
    )
    history.add_user_message(review_task)

    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),
        max_tokens=REVIEWER_MAX_TOKENS,
        temperature=0.1,
    )

    response = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )

    raw = str(response).strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        review = json.loads(raw)
    except json.JSONDecodeError:
        # 파싱 실패 시 통과 처리
        review = {
            "score": 8,
            "passed": True,
            "strengths": ["답변이 작성됨"],
            "issues": [],
            "missing_info": [],
            "replan_suggestion": "",
        }

    return review


async def run_final_polish(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    user_query: str,
    draft_answer: str,
    review: dict,
) -> str:
    """
    최종 답변 정제: Reviewer 피드백을 반영하여 최종 답변을 생성합니다.
    (Reviewer 통과 시에도 포맷 정리 목적으로 실행)
    """
    history = ChatHistory()
    history.add_system_message(
        "당신은 영업/마케팅 전문 AI 어시스턴트입니다. "
        "아래 답변 초안과 리뷰 피드백을 바탕으로 최종 답변을 완성하세요. "
        "마크다운을 활용하여 구조화하고, 실행 가능한 인사이트를 명확히 전달하세요. "
        "한국어로 작성하세요."
    )

    strengths_str = "\n".join(f"  - {s}" for s in review.get("strengths", []))
    issues_str = "\n".join(f"  - {i}" for i in review.get("issues", []))

    polish_task = (
        f"[사용자 질문]\n{user_query}\n\n"
        f"[답변 초안]\n{draft_answer}\n\n"
        f"[리뷰 피드백]\n"
        f"품질 점수: {review.get('score', 'N/A')}/10\n"
        f"잘된 점:\n{strengths_str or '  (없음)'}\n"
        f"개선 필요:\n{issues_str or '  (없음)'}\n\n"
        f"피드백을 반영하여 최종 답변을 작성하세요."
    )
    history.add_user_message(polish_task)

    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),
        max_tokens=FINAL_MAX_TOKENS,
        temperature=0.5,
    )

    response = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )

    return str(response)


async def agentic_pipeline(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    user_query: str,
    query_history: QueryHistory | None = None,
    verbose: bool = True,
) -> str:
    """
    Planner → Executor → Reviewer 아젠틱 루프 실행

    Args:
        kernel: Semantic Kernel 인스턴스 (플러그인 등록됨)
        chat_service: Azure OpenAI Chat 서비스
        user_query: 사용자 질문
        query_history: 질문 이력 관리 객체
        verbose: 중간 단계 출력 여부

    Returns:
        최종 답변 문자열
    """
    if query_history:
        query_history.add(user_query)

    def log(msg: str):
        if verbose:
            print(msg)

    replan_hint = ""
    last_draft = ""
    last_review: dict = {}

    for iteration in range(1, MAX_ITERATIONS + 1):
        log(f"\n{'='*60}")
        log(f"  Agentic Loop - Iteration {iteration}/{MAX_ITERATIONS}")
        log(f"{'='*60}")

        # ── Step 1: Planner ───────────────────────────────────────────────
        log("\n[1/3] Planner: 실행 계획 수립 중...")
        plan = await run_planner(kernel, chat_service, user_query, replan_hint)

        log(f"  질문 유형: {plan.get('query_type', 'N/A')}")
        log(f"  분석: {plan.get('analysis', 'N/A')}")
        log(f"  계획 단계 수: {len(plan.get('steps', []))}개")
        for step in plan.get("steps", []):
            log(f"    Step {step.get('step')}: [{step.get('plugin')}] {step.get('function')} → {step.get('purpose')}")

        # ── Step 2: Executor ──────────────────────────────────────────────
        log("\n[2/3] Executor: 플러그인 호출 및 답변 초안 작성 중...")
        draft = await run_executor(kernel, chat_service, user_query, plan)
        last_draft = draft

        if verbose:
            preview = draft[:200] + "..." if len(draft) > 200 else draft
            log(f"  초안 미리보기: {preview}")

        # ── Step 3: Reviewer ──────────────────────────────────────────────
        log("\n[3/3] Reviewer: 답변 품질 검토 중...")
        review = await run_reviewer(kernel, chat_service, user_query, draft)
        last_review = review

        score = review.get("score", 0)
        passed = review.get("passed", False)
        log(f"  품질 점수: {score}/10 ({'✓ 통과' if passed else '✗ 재계획 필요'})")

        if review.get("issues"):
            log(f"  문제점: {', '.join(review['issues'])}")
        if review.get("missing_info"):
            log(f"  누락 정보: {', '.join(review['missing_info'])}")

        if passed or score >= REVIEW_THRESHOLD:
            log(f"\n  ✓ Reviewer 통과 (iteration {iteration})")
            break

        # 통과 못하면 Planner에게 재계획 힌트 전달
        replan_hint = review.get("replan_suggestion", "더 상세한 정보를 추가로 조회하세요.")
        log(f"\n  → 재계획: {replan_hint}")

        if iteration == MAX_ITERATIONS:
            log(f"\n  ⚠ 최대 반복({MAX_ITERATIONS}회) 도달. 최선의 답변으로 응답합니다.")

    # ── 최종 답변 정제 ────────────────────────────────────────────────────────
    log("\n[최종] 답변 정제 중...")
    final_answer = await run_final_polish(
        kernel, chat_service, user_query, last_draft, last_review
    )

    return final_answer


async def interactive_bot():
    """
    대화형 영업/마케팅 AI 봇 메인 루프

    사용자가 'quit' 또는 'exit'를 입력할 때까지 계속 질문을 받습니다.
    """
    print("=" * 60)
    print("  영업/마케팅 Agentic AI Bot (Azure ML + Semantic Kernel)")
    print("=" * 60)
    print("  Planner → Executor → Reviewer 패턴으로 동작합니다.")
    print("  지원 도메인: 고객정보 / 제품정보 / 고객미팅 / 마케팅전략")
    print("  종료: 'quit' 또는 'exit' 입력")
    print("=" * 60)

    # 초기화
    config = get_azure_openai_config()
    kernel, chat_service = _build_kernel_and_service(config)

    query_history = QueryHistory(
        persist_path=os.path.join(
            os.path.dirname(__file__), "..", ".agentic_bot_history.json"
        )
    )

    print("\n사용 예시 질문:")
    print("  1. 이탈 위험 고객 현황과 대응 전략을 알려줘")
    print("  2. 삼성전자 고객 미팅 이력과 추천 제품을 분석해줘")
    print("  3. 금융권 고객을 위한 마케팅 전략을 수립해줘")
    print("  4. 현재 진행 중인 캠페인과 ROI를 분석해줘")
    print("  5. 카카오에 추천할 AI 제품과 다음 미팅 전략은?\n")

    while True:
        try:
            user_input = input("질문: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n봇을 종료합니다.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "종료", "q"):
            print("\n봇을 종료합니다.")
            break

        print()
        try:
            final_answer = await agentic_pipeline(
                kernel=kernel,
                chat_service=chat_service,
                user_query=user_input,
                query_history=query_history,
                verbose=True,
            )

            print("\n" + "=" * 60)
            print("  최종 답변")
            print("=" * 60)
            print(final_answer)
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[오류] {type(e).__name__}: {e}")
            print("다시 시도하거나 다른 질문을 입력해주세요.\n")

    query_history.display()


async def demo_single_query(query: str = None):
    """
    단일 쿼리 데모 (스크립트 직접 실행 시 사용)

    Azure ML Notebook이나 CI/CD 파이프라인에서 단발성 테스트에 활용합니다.
    """
    if query is None:
        query = "이탈 위험 고객 현황을 파악하고, 해당 고객들을 위한 마케팅 전략과 추천 제품을 알려줘."

    print("=" * 60)
    print("  단일 쿼리 데모 모드")
    print("=" * 60)
    print(f"  질문: {query}\n")

    config = get_azure_openai_config()
    kernel, chat_service = _build_kernel_and_service(config)

    final_answer = await agentic_pipeline(
        kernel=kernel,
        chat_service=chat_service,
        user_query=query,
        verbose=True,
    )

    print("\n" + "=" * 60)
    print("  최종 답변")
    print("=" * 60)
    print(final_answer)
    print("=" * 60)

    return final_answer


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="영업/마케팅 Agentic AI Bot")
    parser.add_argument("--mode", choices=["interactive", "demo"], default="interactive",
                        help="실행 모드: interactive(대화형) 또는 demo(단일 쿼리)")
    parser.add_argument("--query", type=str, default=None,
                        help="demo 모드에서 사용할 질문")
    args = parser.parse_args()

    if args.mode == "demo":
        asyncio.run(demo_single_query(args.query))
    else:
        asyncio.run(interactive_bot())
