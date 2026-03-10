"""
05. Dynamic Agentic AI - LLM이 스스로 판단하는 범용 에이전트

핵심 설계 원칙:
  - 코드는 Tool과 루프만 제공, 어떤 Tool을 몇 번 어떤 순서로 쓸지는 LLM이 결정
  - SK 네이티브 max_auto_invoke_kernel_function_calls 로 Tool 연쇄 호출 허용
  - ReAct System Prompt 로 동적 재조회 행동 유도
  - Tool Progress Filter 로 중간 과정 실시간 표시
  - batch_search Tool 로 여러 항목 병렬 검색 지원

작동 방식 (ReAct Loop - SK 내부에서 자동 처리):
  사용자 입력
      └─ [Reason]  LLM이 요청을 분석하고 실행 계획 수립
          └─ [Act]     적합한 Tool 선택 및 호출
              └─ [Observe] 결과 분석, 추가 조사 항목 파악
                  └─ 추가 조사 필요 → 다시 [Act] 반복
                      └─ 충분한 정보 수집 → 최종 답변 생성

실행:
    python semantic_kernel_agent/05_dynamic_agent.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from semantic_kernel.filters.filter_types import FilterTypes
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext

from config.settings import get_azure_openai_config
from plugins.math_plugin import MathPlugin
from plugins.data_analysis_plugin import DataAnalysisPlugin
from plugins.web_search_plugin import WebSearchPlugin
from utils.query_history import QueryHistory


# ---------------------------------------------------------------------------
# ReAct System Prompt
# 코드 로직이 아닌 System Prompt가 에이전트의 동적 판단 로직을 정의한다.
# ---------------------------------------------------------------------------
DYNAMIC_REACT_SYSTEM_PROMPT = """
당신은 사용자의 어떤 질문도 처리할 수 있는 범용 AI 에이전트입니다.
사용 가능한 도구를 적극적으로 활용하여 완전하고 정확한 답변을 제공하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 작동 방식: ReAct (Reason → Act → Observe → Repeat)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Reason] 사용자 요청을 분석하고 실행 계획을 세웁니다
  - 어떤 정보가 필요한가?
  - 어떤 도구를 어떤 순서로 써야 하는가?
  - 독립적으로 처리 가능한 것과 이전 결과에 의존하는 것을 구분하라

[Act] 계획에 따라 도구를 호출합니다

[Observe] 결과를 분석합니다
  - 요청한 정보가 충분한가?
  - 결과에서 추가로 조사해야 할 새로운 항목(제품명, 기업명, 기술명, 인물명 등)이 나왔는가?
  - 추가 항목이 있으면 → 다시 [Act]로 돌아가 조사하라

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 도구 선택 기준
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Search.search
   - 단일 주제에 대한 최신 정보 검색
   - 언제: 하나의 특정 항목을 조사할 때

2. Search.batch_search  ← 동적 체이닝의 핵심 도구
   - 여러 항목을 동시에 병렬 검색 (단일 검색보다 빠름)
   - 언제: 이전 검색 결과에서 여러 항목(2개 이상)을 발견하여 각각 상세 조사가 필요할 때
   - 예시: 회의록에서 "갤럭시 S25", "HBM3E", "Exynos 2500"이 언급됨
           → batch_search(queries=["갤럭시 S25 상세정보", "HBM3E 기술 정보", "Exynos 2500 스펙"])

3. Search.search_news
   - 최신 뉴스 및 시사 정보 검색
   - 언제: 최근 동향, 시장 변화, 발표 내용 확인 시

4. Math.*
   - 수치 계산이 필요할 때 반드시 사용 (자체 계산 금지)
   - 더하기, 빼기, 곱하기, 나누기, 제곱근, 거듭제곱

5. DataAnalysis.*
   - 여러 데이터 포인트의 통계 분석, 이상값 탐지, 데이터셋 비교

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 동적 재조회 규칙 (가장 중요)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

검색 결과를 받은 후 다음 항목들을 확인하라:

□ 결과에 특정 제품명이 언급되었는가?  → 해당 제품 상세 조사
□ 결과에 기업명/조직명이 언급되었는가? → 해당 기업 정보 조사
□ 결과에 기술명/개념이 언급되었는가?  → 해당 기술 심층 조사
□ 결과에 인물이 언급되었는가?         → 필요시 해당 인물 정보 조사
□ 사용자가 명시적으로 요청한 항목 중 아직 처리되지 않은 것이 있는가? → 계속 진행

위 항목 중 하나라도 해당되면 즉시 추가 도구를 호출하라.
모두 처리되었을 때만 최종 답변을 작성하라.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 오류 처리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 검색 결과 없음: 검색어를 영어 또는 다른 표현으로 바꿔 1회 재시도
- 재시도 후에도 없음: "해당 정보를 찾을 수 없음"으로 표기하고 나머지 진행
- 도구 호출 실패: 다른 도구나 방법으로 대체 시도

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 최종 답변 형식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 한국어로 작성
- 여러 항목이 있는 경우 마크다운 헤더(##, ###)로 구조화
- 검색 출처(URL)를 가능한 포함
- 복잡한 작업: 요약(결론) → 상세 내용 순서로 배치
""".strip()


# ---------------------------------------------------------------------------
# Tool Progress Filter
# SK가 Tool을 자동 호출할 때마다 실행되어 진행 상황을 실시간으로 출력한다.
# ---------------------------------------------------------------------------
async def tool_progress_filter(
    context: FunctionInvocationContext,
    next,
) -> None:
    """SK Function Invocation Filter - Tool 호출 전후에 진행 상황을 출력합니다."""
    plugin = context.function.plugin_name
    func = context.function.name

    # 내부 시스템 함수는 출력 제외, 사용자 정의 Plugin만 표시
    if plugin and plugin not in ("_global_functions_",):
        # arguments 요약 출력 (너무 길면 잘라냄)
        args_str = ""
        if context.arguments:
            parts = []
            for key, val in context.arguments.items():
                val_str = str(val)
                parts.append(f"{key}={val_str[:60]}{'...' if len(val_str) > 60 else ''}")
            args_str = ", ".join(parts)

        print(f"\n  ▶ [Tool] {plugin}.{func}({args_str})")

    await next(context)

    if plugin and plugin not in ("_global_functions_",):
        # 결과 길이만 표시 (결과 내용은 LLM이 처리)
        result = context.result
        result_len = len(str(result.value)) if result and result.value else 0
        print(f"  ◀ [Tool] {plugin}.{func} 완료 ({result_len} chars)")


# ---------------------------------------------------------------------------
# Kernel 초기화
# ---------------------------------------------------------------------------
def build_kernel() -> tuple[sk.Kernel, AzureChatCompletion]:
    """
    SK Kernel을 초기화하고 모든 Plugin과 Filter를 등록합니다.

    Returns:
        (kernel, chat_service) 튜플
    """
    config = get_azure_openai_config()
    kernel = sk.Kernel()

    # Azure OpenAI 서비스 등록
    chat_service = AzureChatCompletion(
        deployment_name=config.deployment_name,
        endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
        service_id="azure_chat",
    )
    kernel.add_service(chat_service)

    # 플러그인 등록 (LLM이 선택할 수 있는 모든 Tool)
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Search")
    kernel.add_plugin(MathPlugin(), plugin_name="Math")
    kernel.add_plugin(DataAnalysisPlugin(), plugin_name="DataAnalysis")

    # Tool 진행 상황 Filter 등록
    kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, tool_progress_filter)

    return kernel, chat_service


def build_execution_settings() -> OpenAIChatPromptExecutionSettings:
    """
    SK Auto Function Calling 실행 설정을 반환합니다.

    max_auto_invoke_kernel_function_calls:
        SK가 단일 get_chat_message_content() 호출 내에서
        자동으로 Tool을 호출할 수 있는 최대 횟수.
        이 값이 높을수록 복잡한 다단계 작업 처리 가능.
        (기본값: 5 → 25로 증가하여 동적 체이닝 허용)
    """
    return OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(
            maximum_auto_invoke_attempts=25,  # 동적 다단계 Tool 호출 허용
        ),
        max_tokens=4000,    # 복잡한 작업의 긴 응답 허용
        temperature=0.1,    # 낮은 온도로 일관된 Tool 선택 유도
    )


# ---------------------------------------------------------------------------
# Dynamic Agent REPL
# ---------------------------------------------------------------------------
async def run_dynamic_agent() -> None:
    """
    Interactive REPL 형태의 Dynamic Agent 실행.

    - 사용자가 어떤 질문을 해도 LLM이 동적으로 Tool을 선택하여 처리
    - 한 세션 동안 ChatHistory가 유지되어 이전 대화 맥락 활용 가능
    - Query History는 최대 10개 저장 (세션 종료 시 표시)
    """
    print("=" * 65)
    print("  Dynamic Agentic AI (Semantic Kernel + Azure ML)")
    print("  LLM이 Tool을 자율 판단하여 어떤 질문도 처리합니다.")
    print("  종료: 'exit' 입력 또는 Ctrl+C")
    print("=" * 65)

    kernel, chat_service = build_kernel()
    execution_settings = build_execution_settings()
    query_history = QueryHistory(
        persist_path=os.path.join(os.path.dirname(__file__), "..", ".query_history.json")
    )

    # 세션 전체에서 공유되는 ChatHistory (대화 맥락 유지)
    history = ChatHistory()
    history.add_system_message(DYNAMIC_REACT_SYSTEM_PROMPT)

    turn = 0
    while True:
        # ------------------------------------------------------------------
        # 사용자 입력
        # ------------------------------------------------------------------
        try:
            user_input = input("\nUser: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n에이전트를 종료합니다.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "종료", "q"):
            print("에이전트를 종료합니다.")
            break
        if user_input.lower() in ("history", "히스토리"):
            query_history.display()
            continue
        if user_input.lower() in ("clear", "초기화"):
            history = ChatHistory()
            history.add_system_message(DYNAMIC_REACT_SYSTEM_PROMPT)
            print("대화 기록이 초기화되었습니다.")
            continue

        # ------------------------------------------------------------------
        # Query History 기록
        # ------------------------------------------------------------------
        query_history.add(user_input)
        turn += 1
        print(f"\n[Turn {turn}] 처리 시작...")
        print("-" * 65)

        # ------------------------------------------------------------------
        # SK 네이티브 Auto Function Calling 실행
        #
        # 이 한 줄이 전부입니다.
        # - LLM이 Tool 선택, 호출 횟수, 체이닝 순서를 완전히 자율 결정
        # - SK가 FunctionCallContent를 감지하면 자동으로 Tool 실행
        # - Tool 결과를 History에 추가하고 LLM에 재전달
        # - LLM이 "충분하다"고 판단할 때까지 최대 25회 반복
        # - tool_progress_filter가 각 Tool 호출 시 진행 상황 출력
        # ------------------------------------------------------------------
        history.add_user_message(user_input)
        try:
            response = await chat_service.get_chat_message_content(
                chat_history=history,
                settings=execution_settings,
                kernel=kernel,
            )
        except Exception as e:
            print(f"\n[오류] API 호출 실패: {e}")
            history.messages.pop()  # 실패한 user message 제거
            continue

        history.add_message(response)

        # ------------------------------------------------------------------
        # 최종 응답 출력
        # ------------------------------------------------------------------
        print(f"\n{'=' * 65}")
        print(f"[Agent 최종 응답]")
        print("=" * 65)
        print(str(response))
        print()

    # 세션 종료 시 Query History 출력
    query_history.display()


# ---------------------------------------------------------------------------
# 시나리오 테스트 (비대화형)
# ---------------------------------------------------------------------------
async def run_scenario_tests() -> None:
    """
    대화형 입력 없이 미리 정해진 시나리오로 동적 에이전트를 테스트합니다.
    CI/CD 또는 Azure ML Job에서 실행할 때 사용합니다.
    """
    kernel, chat_service = build_kernel()
    execution_settings = build_execution_settings()
    query_history = QueryHistory()

    scenarios = [
        # 시나리오 1: 단순 계산 (Tool 1회 호출)
        "15의 3제곱을 계산해줘",

        # 시나리오 2: 단일 검색 (Tool 1회 호출)
        "Semantic Kernel이 무엇인지 간략히 설명해줘",

        # 시나리오 3: 복합 쿼리 - 검색 후 발견된 항목 추가 조사
        # LLM이 스스로: ① Azure ML 검색 → ② 결과에서 관련 기술 발견
        #               → ③ batch_search로 관련 기술 병렬 조사 결정
        (
            "Azure ML의 주요 기능을 검색하고, "
            "검색 결과에서 언급되는 핵심 기술이나 서비스가 있으면 "
            "각각 상세하게 추가 조사해줘."
        ),
    ]

    for i, query in enumerate(scenarios, 1):
        print(f"\n{'#' * 65}")
        print(f"# 시나리오 {i}")
        print(f"{'#' * 65}")

        history = ChatHistory()
        history.add_system_message(DYNAMIC_REACT_SYSTEM_PROMPT)
        history.add_user_message(query)
        query_history.add(query)

        print(f"User: {query}\n")
        print("-" * 65)

        try:
            response = await chat_service.get_chat_message_content(
                chat_history=history,
                settings=execution_settings,
                kernel=kernel,
            )
            history.add_message(response)
            print(f"\n[Agent]\n{response}\n")
        except Exception as e:
            print(f"[오류] {e}\n")

    query_history.display()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dynamic Agentic AI Agent")
    parser.add_argument(
        "--test",
        action="store_true",
        help="대화형 입력 없이 미리 정해진 시나리오 테스트 실행",
    )
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_scenario_tests())
    else:
        asyncio.run(run_dynamic_agent())
