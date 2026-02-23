"""
02. Semantic Kernel Function Calling (Tool Use)

AI가 외부 함수(Plugin)를 호출하는 기본 Function Calling 예제입니다.
Agentic AI의 핵심 구성 요소인 Tool Use를 보여줍니다.

핵심 개념:
- Kernel Function: AI가 호출할 수 있는 네이티브 Python 함수
- Plugin: 관련 함수들의 집합
- ToolCallBehavior: AI가 어떻게 함수를 호출할지 제어
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
from plugins.web_search_plugin import WebSearchPlugin


async def function_calling_example():
    """Function Calling 예제"""

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

    # 플러그인 등록 (AI가 사용할 수 있는 Tool 등록)
    kernel.add_plugin(MathPlugin(), plugin_name="Math")
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Search")

    print("=== Semantic Kernel Function Calling 예제 ===")
    print("등록된 플러그인:", [p for p in kernel.plugins])
    print()

    # Auto Function Calling 설정
    # - AUTO: AI가 필요 시 자동으로 함수를 선택하고 호출
    execution_settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(
            filters={"included_plugins": ["Math", "Search"]}
        ),
        max_tokens=800,
        temperature=0.1,  # 계산 작업이므로 낮은 온도 설정
    )

    history = ChatHistory()
    history.add_system_message(
        "당신은 수학 계산과 정보 검색을 도와주는 도우미입니다. "
        "제공된 함수를 적극 활용하여 정확한 답변을 제공하세요. "
        "한국어로 답변해주세요."
    )

    # 테스트 쿼리들
    queries = [
        "245 곱하기 37을 계산해줘",
        "1024의 제곱근은 얼마야?",
        "Semantic Kernel에 대해 검색해줘",
        "15의 3제곱을 계산하고, 현재 날짜도 알려줘",  # 복합 쿼리 - 여러 함수 호출
    ]

    for query in queries:
        history.add_user_message(query)
        print(f"User: {query}")

        response = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        history.add_assistant_message(str(response))
        print(f"Assistant: {response}")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(function_calling_example())
