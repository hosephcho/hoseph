"""
01. Semantic Kernel 기본 채팅 완성 (Azure ML 환경)

이 예제는 Azure OpenAI와 Semantic Kernel을 연결하는
가장 기본적인 채팅 완성(Chat Completion) 구현입니다.

Azure ML 환경:
- Managed Identity 인증 또는 API Key 인증 모두 지원
- azure-identity 패키지를 통한 DefaultAzureCredential 사용
"""

import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory

from config.settings import get_azure_openai_config
from utils.query_history import QueryHistory


async def basic_chat_example():
    """기본 채팅 완성 예제"""

    # 1. 설정 로드
    config = get_azure_openai_config()

    # Query History 초기화 (최대 10개 유지, 선택적 파일 영속화)
    query_history = QueryHistory(
        persist_path=os.path.join(os.path.dirname(__file__), "..", ".query_history.json")
    )

    # 2. Semantic Kernel 인스턴스 생성
    kernel = sk.Kernel()

    # 3. Azure OpenAI Chat Completion 서비스 등록
    # Azure ML Managed Identity 사용 시: api_key=None으로 설정하면
    # DefaultAzureCredential을 통해 자동 인증됩니다
    if config.api_key:
        # API Key 방식 (로컬 개발 / 명시적 키 사용)
        chat_service = AzureChatCompletion(
            deployment_name=config.deployment_name,
            endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            service_id="azure_chat",
        )
    else:
        # Managed Identity 방식 (Azure ML Compute Instance 권장)
        from azure.identity.aio import DefaultAzureCredential
        ad_token_provider = DefaultAzureCredential()

        chat_service = AzureChatCompletion(
            deployment_name=config.deployment_name,
            endpoint=config.endpoint,
            ad_token_provider=ad_token_provider,
            api_version=config.api_version,
            service_id="azure_chat",
        )

    kernel.add_service(chat_service)

    # 4. 채팅 히스토리 생성
    history = ChatHistory()
    history.add_system_message(
        "당신은 Azure ML과 데이터 사이언스 전문가입니다. "
        "한국어로 명확하고 친절하게 답변해주세요."
    )

    # 5. 대화 실행
    print("=== Semantic Kernel 기본 채팅 예제 ===\n")

    questions = [
        "Azure ML에서 Semantic Kernel을 사용하는 주요 장점은 무엇인가요?",
        "Agentic AI란 무엇인지 간단히 설명해주세요.",
    ]

    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

    for question in questions:
        query_history.add(question)          # Query History에 기록
        history.add_user_message(question)
        print(f"User: {question}")

        # 실행 설정
        execution_settings = OpenAIChatPromptExecutionSettings(
            max_tokens=500,
            temperature=0.7,
        )

        # 응답 생성
        response = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        history.add_assistant_message(str(response))
        print(f"Assistant: {response}\n")
        print("-" * 60)

    # 세션 종료 시 Query History 출력
    query_history.display()


if __name__ == "__main__":
    asyncio.run(basic_chat_example())
