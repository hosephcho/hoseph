"""
03. Auto Function Calling Agent (핵심 Agentic AI 구현)

이것이 Agentic AI의 핵심입니다.
AI가 목표를 달성하기 위해 자율적으로 계획하고,
여러 함수를 순서대로 호출하며, 중간 결과를 분석하여
최종 답변을 도출하는 ReAct(Reason + Act) 루프를 구현합니다.

동작 방식:
1. 사용자 입력 수신
2. AI가 목표 달성을 위한 계획 수립
3. 필요한 함수(Tool) 선택 및 호출
4. 결과 분석 및 다음 행동 결정
5. 목표 달성 시 최종 응답 생성

Azure ML 활용 시나리오:
- 데이터 분석 자동화
- 모델 성능 비교 및 리포팅
- 파이프라인 상태 모니터링
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
from semantic_kernel.contents.utils.author_role import AuthorRole

from config.settings import get_azure_openai_config
from plugins.math_plugin import MathPlugin
from plugins.data_analysis_plugin import DataAnalysisPlugin
from plugins.web_search_plugin import WebSearchPlugin
from utils.query_history import QueryHistory


async def agentic_loop(
    kernel: sk.Kernel,
    chat_service,
    history: ChatHistory,
    execution_settings,
    user_input: str,
    query_history: QueryHistory | None = None,
    max_iterations: int = 10,
):
    """
    Agentic AI의 핵심 루프 구현

    AI가 목표를 달성할 때까지 반복적으로:
    1. 다음 행동 결정 (어떤 함수를 호출할지)
    2. 함수 호출 및 결과 수집
    3. 결과를 바탕으로 다음 단계 진행
    """
    if query_history is not None:
        query_history.add(user_input)        # Query History에 기록
    history.add_user_message(user_input)
    print(f"\n[Agent] 목표: {user_input}")
    print("=" * 60)

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        response = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        # 함수 호출이 포함된 응답 처리
        tool_calls_made = False
        if hasattr(response, 'items'):
            for item in response.items:
                # FunctionCallContent: AI가 함수 호출을 요청
                item_type = type(item).__name__
                if item_type == "FunctionCallContent":
                    tool_calls_made = True
                    print(f"  [Tool Call] {item.plugin_name}.{item.function_name}({item.arguments})")

        # AI가 더 이상 함수를 호출하지 않으면 최종 응답
        if not tool_calls_made:
            history.add_message(response)
            print(f"\n[Agent] 최종 응답:\n{response}")
            return str(response)

        # 함수 호출 결과를 히스토리에 추가하고 계속 진행
        history.add_message(response)

    print("[Agent] 최대 반복 횟수 도달")
    return "최대 반복 횟수에 도달했습니다."


async def auto_function_calling_agent():
    """Auto Function Calling을 활용한 Agentic AI 에이전트"""

    config = get_azure_openai_config()
    kernel = sk.Kernel()

    query_history = QueryHistory(
        persist_path=os.path.join(os.path.dirname(__file__), "..", ".query_history.json")
    )

    chat_service = AzureChatCompletion(
        deployment_name=config.deployment_name,
        endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
        service_id="azure_chat",
    )
    kernel.add_service(chat_service)

    # 에이전트가 사용할 플러그인 등록
    kernel.add_plugin(MathPlugin(), plugin_name="Math")
    kernel.add_plugin(DataAnalysisPlugin(), plugin_name="DataAnalysis")
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Search")

    # Auto Function Calling 설정
    # AI가 필요에 따라 자동으로 함수를 선택하고 여러 번 호출 가능
    execution_settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
        max_tokens=1500,
        temperature=0.2,
        # Azure OpenAI에서 최대 함수 호출 반복 횟수 설정
        # 기본값은 1이므로 Agentic AI를 위해 늘려야 함
    )

    # 에이전트 시스템 프롬프트 설정
    history = ChatHistory()
    history.add_system_message("""
당신은 데이터 분석 전문 AI 에이전트입니다.
주어진 목표를 달성하기 위해 사용 가능한 도구(함수)를 적극적으로 활용하세요.

사용 가능한 도구:
- Math 플러그인: 수학 계산 (더하기, 빼기, 곱하기, 나누기, 제곱근, 거듭제곱)
- DataAnalysis 플러그인: 데이터 통계 분석, 이상값 탐지, 데이터셋 비교
- Search 플러그인: 정보 검색, 현재 날짜 조회

지침:
1. 복잡한 작업은 여러 단계로 나누어 순차적으로 처리하세요
2. 계산이 필요하면 반드시 Math 또는 DataAnalysis 도구를 사용하세요
3. 각 단계의 결과를 다음 단계에 활용하세요
4. 최종 결과를 명확하고 구조적으로 정리하여 한국어로 답변하세요
""")

    print("=== Semantic Kernel Auto Function Calling Agent ===")
    print("(Azure ML Agentic AI 핵심 구현)\n")

    # 시나리오 1: 복합 데이터 분석 작업
    task1 = """
    다음 두 그룹의 데이터를 분석하고 비교 보고서를 작성해줘:

    그룹 A (실험군): 85, 92, 78, 95, 88, 102, 75, 91, 87, 93
    그룹 B (대조군): 72, 68, 75, 71, 79, 65, 73, 70, 68, 74

    각 그룹의 기초 통계를 계산하고, 이상값이 있는지 확인한 다음,
    두 그룹을 비교하여 결론을 내려줘.
    """

    await agentic_loop(kernel, chat_service, history, execution_settings, task1, query_history)

    print("\n" + "=" * 60)

    # 시나리오 2: 정보 검색 + 계산 복합 작업
    history2 = ChatHistory()
    history2.add_system_message(history.messages[0].content)

    task2 = """
    Semantic Kernel이 무엇인지 검색하고,
    그 다음 2의 10제곱과 현재 날짜를 확인한 후
    간단한 요약 보고서를 작성해줘.
    """

    await agentic_loop(kernel, chat_service, history2, execution_settings, task2, query_history)

    # 세션 종료 시 Query History 출력
    query_history.display()


if __name__ == "__main__":
    asyncio.run(auto_function_calling_agent())
