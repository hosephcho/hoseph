"""
웹 검색 플러그인 (시뮬레이션)

실제 환경에서는 Bing Search API, Azure AI Search 등과 연동합니다.
이 예제에서는 Agentic AI의 Tool Use 개념 시연을 위한 시뮬레이션 버전입니다.

실제 Azure AI Search 연동:
    from azure.search.documents import SearchClient
    from azure.identity import DefaultAzureCredential
    client = SearchClient(endpoint, index_name, DefaultAzureCredential())
"""

from datetime import datetime
from typing import Annotated
from semantic_kernel.functions import kernel_function


class WebSearchPlugin:
    """검색 기능을 제공하는 플러그인 (데모용 시뮬레이션)"""

    # 시뮬레이션 데이터
    _knowledge_base = {
        "azure ml": {
            "title": "Azure Machine Learning",
            "summary": (
                "Azure ML은 Microsoft의 클라우드 기반 머신러닝 플랫폼입니다. "
                "데이터 준비, 모델 훈련, 배포, 모니터링을 위한 통합 환경을 제공합니다. "
                "Compute Instance, Compute Cluster, 자동화된 ML(AutoML), "
                "MLflow 통합 등의 기능을 포함합니다."
            ),
        },
        "semantic kernel": {
            "title": "Semantic Kernel",
            "summary": (
                "Semantic Kernel은 Microsoft가 개발한 오픈소스 SDK로, "
                "AI 모델(GPT, Claude 등)을 기존 애플리케이션에 통합하는 데 사용됩니다. "
                "Function Calling, Memory, Planner 등의 기능을 제공하며 "
                "Python, C#, Java를 지원합니다."
            ),
        },
        "agentic ai": {
            "title": "Agentic AI",
            "summary": (
                "Agentic AI는 목표를 달성하기 위해 자율적으로 계획하고 행동하는 AI 시스템입니다. "
                "도구(Tools/Functions)를 호출하고, 결과를 분석하여 다음 행동을 결정하는 "
                "반복적인 루프(ReAct Loop) 방식으로 동작합니다."
            ),
        },
        "function calling": {
            "title": "Function Calling (Tool Use)",
            "summary": (
                "Function Calling은 LLM이 외부 함수나 API를 호출할 수 있는 기능입니다. "
                "AI가 어떤 함수를 언제 호출할지 스스로 판단하며, "
                "Semantic Kernel에서는 Auto Function Calling Behavior로 구현됩니다."
            ),
        },
    }

    @kernel_function(
        name="search",
        description="주어진 키워드로 정보를 검색합니다. Azure ML, Semantic Kernel, AI 관련 정보를 찾을 수 있습니다.",
    )
    def search(
        self,
        query: Annotated[str, "검색할 키워드 또는 질문"],
        max_results: Annotated[int, "반환할 최대 결과 수 (기본값: 3)"] = 3,
    ) -> str:
        """키워드로 정보를 검색합니다"""
        query_lower = query.lower()
        results = []

        for key, value in self._knowledge_base.items():
            if any(word in query_lower for word in key.split()):
                results.append(value)

        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다."

        results = results[:max_results]
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r['title']}\n{r['summary']}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"검색 결과 ({timestamp}):\n\n" + "\n\n".join(formatted)

    @kernel_function(
        name="get_current_date",
        description="현재 날짜와 시간을 반환합니다",
    )
    def get_current_date(self) -> str:
        """현재 날짜와 시간을 반환합니다"""
        now = datetime.now()
        return f"현재 날짜 및 시간: {now.strftime('%Y년 %m월 %d일 %H시 %M분')}"
