"""
04. Multi-Agent 협업 시스템

여러 전문화된 에이전트가 협력하여 복잡한 작업을 수행합니다.
각 에이전트는 특정 역할을 담당하며, 에이전트 간에 결과를 전달합니다.

아키텍처:
                    [Orchestrator Agent]
                    /         |          \\
         [Researcher]  [Analyst]   [Reporter]
          (정보 수집)  (데이터 분석)  (보고서 작성)

Azure ML 실제 활용 시나리오:
- 데이터 수집 에이전트 → 전처리 에이전트 → 모델 선택 에이전트 → 결과 보고 에이전트
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

from config.settings import get_azure_openai_config
from plugins.math_plugin import MathPlugin
from plugins.data_analysis_plugin import DataAnalysisPlugin
from plugins.web_search_plugin import WebSearchPlugin
from utils.query_history import QueryHistory


def create_agent(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    role: str,
    system_prompt: str,
    tools: list[str] | None = None,
) -> tuple[ChatHistory, OpenAIChatPromptExecutionSettings]:
    """
    전문화된 에이전트를 생성합니다.

    Returns:
        (ChatHistory, ExecutionSettings) 튜플
    """
    history = ChatHistory()
    history.add_system_message(system_prompt)

    if tools:
        settings = OpenAIChatPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                filters={"included_plugins": tools}
            ),
            max_tokens=1000,
            temperature=0.3,
        )
    else:
        settings = OpenAIChatPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),
            max_tokens=1000,
            temperature=0.5,
        )

    print(f"  [Agent 생성] {role}")
    return history, settings


async def run_agent(
    kernel: sk.Kernel,
    chat_service: AzureChatCompletion,
    agent_name: str,
    history: ChatHistory,
    settings: OpenAIChatPromptExecutionSettings,
    task: str,
    query_history: QueryHistory | None = None,
) -> str:
    """에이전트에 작업을 할당하고 결과를 반환합니다"""
    if query_history is not None:
        query_history.add(f"[{agent_name}] {task[:80]}{'...' if len(task) > 80 else ''}")
    history.add_user_message(task)
    print(f"\n[{agent_name}] 작업 수행 중...")

    response = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )
    history.add_message(response)
    result = str(response)
    print(f"[{agent_name}] 완료")
    return result


async def multi_agent_pipeline():
    """
    Multi-Agent 파이프라인 실행

    시나리오: Azure ML 모델 성능 분석 보고서 작성
    - Researcher: 관련 정보 수집
    - Analyst: 데이터 분석 및 통계 계산
    - Reporter: 최종 보고서 작성
    """

    config = get_azure_openai_config()
    kernel = sk.Kernel()

    query_history = QueryHistory(
        persist_path=os.path.join(os.path.dirname(__file__), "..", ".query_history.json")
    )

    # 공유 서비스 등록 (모든 에이전트가 동일한 서비스 사용)
    chat_service = AzureChatCompletion(
        deployment_name=config.deployment_name,
        endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
        service_id="azure_chat",
    )
    kernel.add_service(chat_service)

    # 공유 플러그인 등록
    kernel.add_plugin(MathPlugin(), plugin_name="Math")
    kernel.add_plugin(DataAnalysisPlugin(), plugin_name="DataAnalysis")
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Search")

    print("=== Multi-Agent 협업 시스템 ===")
    print("에이전트 초기화 중...\n")

    # --- 에이전트 1: Researcher (정보 수집 전문) ---
    researcher_history, researcher_settings = create_agent(
        kernel, chat_service,
        role="Researcher",
        system_prompt=(
            "당신은 정보 수집 전문 에이전트입니다. "
            "주어진 주제에 대해 검색 도구를 활용하여 관련 정보를 수집하고 "
            "정리하는 것이 주요 역할입니다. 한국어로 답변하세요."
        ),
        tools=["Search"],
    )

    # --- 에이전트 2: Analyst (데이터 분석 전문) ---
    analyst_history, analyst_settings = create_agent(
        kernel, chat_service,
        role="Analyst",
        system_prompt=(
            "당신은 데이터 분석 전문 에이전트입니다. "
            "수치 데이터의 통계 분석, 이상값 탐지, 수학 계산을 수행합니다. "
            "분석 결과를 명확하고 구체적으로 제시하세요. 한국어로 답변하세요."
        ),
        tools=["Math", "DataAnalysis"],
    )

    # --- 에이전트 3: Reporter (보고서 작성 전문) ---
    reporter_history, reporter_settings = create_agent(
        kernel, chat_service,
        role="Reporter",
        system_prompt=(
            "당신은 보고서 작성 전문 에이전트입니다. "
            "다른 에이전트들의 분석 결과를 종합하여 명확하고 구조화된 "
            "최종 보고서를 작성합니다. 마크다운 형식으로 작성하세요. 한국어로 작성하세요."
        ),
        tools=None,  # 보고서 작성 에이전트는 도구 사용 안함
    )

    print("\n파이프라인 실행 시작")
    print("=" * 60)

    # === Step 1: Researcher가 배경 정보 수집 ===
    research_result = await run_agent(
        kernel, chat_service,
        agent_name="Researcher",
        history=researcher_history,
        settings=researcher_settings,
        task=(
            "Azure ML과 Semantic Kernel에 대한 정보를 검색하고, "
            "현재 날짜도 확인해서 배경 정보를 요약해줘."
        ),
        query_history=query_history,
    )

    # === Step 2: Analyst가 모델 성능 데이터 분석 ===
    analysis_result = await run_agent(
        kernel, chat_service,
        agent_name="Analyst",
        history=analyst_history,
        settings=analyst_settings,
        task=(
            "아래 두 모델의 정확도 데이터를 분석해줘:\n\n"
            "모델 A (기존 모델): 0.82, 0.85, 0.83, 0.87, 0.84, 0.86, 0.81, 0.88, 0.85, 0.83\n"
            "모델 B (신규 모델): 0.89, 0.91, 0.88, 0.92, 0.90, 0.87, 0.93, 0.91, 0.89, 0.92\n\n"
            "각 모델의 기초 통계를 계산하고, 이상값이 있는지 확인하고, "
            "두 모델을 비교 분석해줘. 퍼센트로 계산할 때는 Math 도구를 사용해."
        ),
        query_history=query_history,
    )

    # === Step 3: Reporter가 최종 보고서 작성 ===
    final_report = await run_agent(
        kernel, chat_service,
        agent_name="Reporter",
        history=reporter_history,
        settings=reporter_settings,
        task=(
            f"아래 두 에이전트의 분석 결과를 바탕으로 최종 보고서를 작성해줘.\n\n"
            f"## Researcher의 배경 조사 결과:\n{research_result}\n\n"
            f"## Analyst의 데이터 분석 결과:\n{analysis_result}\n\n"
            f"최종 보고서에는 다음을 포함해줘:\n"
            f"1. 프로젝트 개요\n"
            f"2. 기술 스택 요약\n"
            f"3. 모델 성능 분석 결과\n"
            f"4. 결론 및 권고사항"
        ),
        query_history=query_history,
    )

    print("\n" + "=" * 60)
    print("=== 최종 보고서 ===")
    print("=" * 60)
    print(final_report)

    # 세션 종료 시 Query History 출력
    query_history.display()


if __name__ == "__main__":
    asyncio.run(multi_agent_pipeline())
