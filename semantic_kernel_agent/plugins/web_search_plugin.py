"""
웹 검색 플러그인 (실제 API 연동)

지원하는 검색 엔진 (우선순위 순):
  1. Bing Web Search API  - BING_SEARCH_API_KEY 환경 변수 설정 시 사용
  2. SerpAPI (Google)     - SERPAPI_API_KEY 환경 변수 설정 시 사용
  3. DuckDuckGo           - API Key 불필요, 자동 fallback

환경 변수 설정 (.env 또는 Azure ML Environment Variables):
    BING_SEARCH_API_KEY=<Azure Cognitive Services Bing Search v7 키>
    SERPAPI_API_KEY=<SerpAPI 키 (https://serpapi.com)>

Bing Search 리소스 생성:
    Azure Portal > Cognitive Services > Bing Search v7 > 키 복사
    또는: az cognitiveservices account keys list --name <name> --resource-group <rg>
"""

import os
import json
from datetime import datetime
from typing import Annotated

import requests
from semantic_kernel.functions import kernel_function

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -----------------------------------------------------------------------
# API Key 설정 (없으면 DuckDuckGo fallback 자동 사용)
# -----------------------------------------------------------------------
# Bing Web Search API v7
# Azure Portal > Cognitive Services > Bing Search v7 에서 발급
# https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
BING_SEARCH_API_KEY = os.environ.get("BING_SEARCH_API_KEY", "")  # 발급 후 .env에 입력

# SerpAPI (Google 검색 결과 스크래핑 서비스)
# https://serpapi.com/manage-api-key
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")  # 발급 후 .env에 입력

# -----------------------------------------------------------------------
# 엔드포인트
# -----------------------------------------------------------------------
_BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
_SERPAPI_ENDPOINT = "https://serpapi.com/search"
_DDG_ENDPOINT = "https://api.duckduckgo.com/"  # 무료, API Key 불필요


def _search_bing(query: str, max_results: int, market: str) -> list[dict]:
    """Bing Web Search API v7 호출"""
    headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
    params = {
        "q": query,
        "count": max_results,
        "mkt": market,        # "ko-KR" | "en-US" 등
        "safeSearch": "Moderate",
        "textDecorations": False,
        "textFormat": "Raw",
    }
    resp = requests.get(_BING_ENDPOINT, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("webPages", {}).get("value", [])[:max_results]:
        results.append({
            "title": item.get("name", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
        })
    return results


def _search_serpapi(query: str, max_results: int, market: str) -> list[dict]:
    """SerpAPI (Google Search) 호출"""
    # market 예: "ko-KR" → hl=ko, gl=KR
    lang = market.split("-")[0] if "-" in market else "ko"
    country = market.split("-")[1].lower() if "-" in market else "kr"

    params = {
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "engine": "google",
        "hl": lang,
        "gl": country,
        "num": max_results,
    }
    resp = requests.get(_SERPAPI_ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic_results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return results


def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    """
    DuckDuckGo Instant Answer API (무료, API Key 불필요)

    주의: 상세 검색 결과가 아닌 인스턴트 답변(Instant Answer) 기반이며,
          결과가 없을 수 있습니다. 중요한 정보는 Bing/SerpAPI를 권장합니다.
    """
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    resp = requests.get(_DDG_ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []

    # Abstract (주요 정보)
    if data.get("AbstractText"):
        results.append({
            "title": data.get("Heading", query),
            "url": data.get("AbstractURL", ""),
            "snippet": data["AbstractText"],
        })

    # Related Topics
    for topic in data.get("RelatedTopics", [])[:max_results - len(results)]:
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title": topic.get("Text", "")[:80],
                "url": topic.get("FirstURL", ""),
                "snippet": topic.get("Text", ""),
            })

    return results[:max_results]


class WebSearchPlugin:
    """
    실제 웹 검색 기능을 제공하는 플러그인.

    우선순위:
      1. Bing Search API  (BING_SEARCH_API_KEY 설정 시)
      2. SerpAPI          (SERPAPI_API_KEY 설정 시)
      3. DuckDuckGo       (API Key 없이 자동 fallback)
    """

    @kernel_function(
        name="search",
        description=(
            "인터넷에서 최신 정보를 검색합니다. "
            "뉴스, 기술 문서, 일반 지식 등 모든 키워드 검색에 사용하세요."
        ),
    )
    def search(
        self,
        query: Annotated[str, "검색할 키워드 또는 질문 (한국어 또는 영어)"],
        max_results: Annotated[int, "반환할 최대 결과 수 (기본값: 5, 최대: 10)"] = 5,
        market: Annotated[str, "검색 언어/지역 코드 (기본값: ko-KR)"] = "ko-KR",
    ) -> str:
        """웹에서 실시간으로 정보를 검색하고 결과를 반환합니다."""
        max_results = min(max(1, max_results), 10)
        engine_used = "unknown"

        try:
            if BING_SEARCH_API_KEY:
                results = _search_bing(query, max_results, market)
                engine_used = "Bing Web Search"
            elif SERPAPI_API_KEY:
                results = _search_serpapi(query, max_results, market)
                engine_used = "SerpAPI (Google)"
            else:
                results = _search_duckduckgo(query, max_results)
                engine_used = "DuckDuckGo (fallback, API Key 없음)"
        except requests.exceptions.HTTPError as e:
            return f"검색 API 오류 (HTTP {e.response.status_code}): {str(e)}"
        except requests.exceptions.ConnectionError:
            return "검색 실패: 네트워크 연결을 확인하세요."
        except requests.exceptions.Timeout:
            return "검색 실패: 요청 시간이 초과되었습니다."
        except Exception as e:
            return f"검색 중 예상치 못한 오류가 발생했습니다: {str(e)}"

        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다. (엔진: {engine_used})"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"검색 결과 [{engine_used}] ({timestamp}) - 쿼리: '{query}'\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}")
            if r.get("url"):
                lines.append(f"     URL: {r['url']}")
            lines.append(f"     {r['snippet']}")
            lines.append("")

        return "\n".join(lines)

    @kernel_function(
        name="search_news",
        description="최신 뉴스를 검색합니다. 시사, 기술 동향, 산업 뉴스 검색에 사용하세요.",
    )
    def search_news(
        self,
        query: Annotated[str, "뉴스 검색 키워드"],
        max_results: Annotated[int, "반환할 최대 뉴스 수 (기본값: 5)"] = 5,
        market: Annotated[str, "검색 언어/지역 코드 (기본값: ko-KR)"] = "ko-KR",
    ) -> str:
        """최신 뉴스를 검색합니다 (Bing News API 사용, 없으면 일반 검색으로 대체)."""
        max_results = min(max(1, max_results), 10)

        # Bing News API (Bing Search API Key 공용 사용)
        if BING_SEARCH_API_KEY:
            try:
                headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
                params = {
                    "q": query,
                    "count": max_results,
                    "mkt": market,
                    "freshness": "Week",  # 최근 1주일 뉴스
                    "safeSearch": "Moderate",
                }
                resp = requests.get(
                    "https://api.bing.microsoft.com/v7.0/news/search",
                    headers=headers,
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()

                articles = data.get("value", [])[:max_results]
                if articles:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    lines = [f"뉴스 검색 결과 [Bing News] ({timestamp}) - 쿼리: '{query}'\n"]
                    for i, a in enumerate(articles, 1):
                        pub_date = a.get("datePublished", "")[:10]
                        lines.append(f"[{i}] {a.get('name', '')}  ({pub_date})")
                        lines.append(f"     URL: {a.get('url', '')}")
                        lines.append(f"     {a.get('description', '')}")
                        lines.append("")
                    return "\n".join(lines)
            except Exception:
                pass  # 뉴스 API 실패 시 일반 검색으로 fallback

        # Bing News 실패 또는 키 없음 → 일반 검색에 "뉴스" 추가
        return self.search(f"{query} 뉴스", max_results, market)

    @kernel_function(
        name="get_current_date",
        description="현재 날짜와 시간을 반환합니다",
    )
    def get_current_date(self) -> str:
        """현재 날짜와 시간을 반환합니다"""
        now = datetime.now()
        return f"현재 날짜 및 시간: {now.strftime('%Y년 %m월 %d일 %H시 %M분')}"
