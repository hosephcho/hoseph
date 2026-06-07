"""
석유화학 뉴스 수집 플러그인

RSS 피드 및 웹 검색을 통해 주요 석유화학 화학물질 관련 뉴스를 수집하고
카테고리별로 구조화합니다.

무료 데이터 소스:
  - ICIS: https://www.icis.com/explore/resources/news/feed/
  - Chemical Week: https://chemweek.com/CW/feeds/rss/
  - Chemical Engineering: https://www.chemengonline.com/feed/

유료 API 연동 시:
  - S&P Global (Platts): SPGLOBAL_API_KEY 설정
  - ICIS Data API: ICIS_API_KEY 설정
"""

import json
import re
from datetime import datetime, timezone
from typing import Annotated

import requests
from semantic_kernel.functions import kernel_function

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

PETROCHEM_RSS_FEEDS = {
    "icis": "https://www.icis.com/explore/resources/news/feed/",
    "chemweek": "https://chemweek.com/CW/feeds/rss/",
    "chemical_engineering": "https://www.chemengonline.com/feed/",
}

# 화학물질 키워드 (소문자, 검색 필터링에 사용)
TARGET_CHEMICALS = [
    "ethylene", "에틸렌",
    "propylene", "프로필렌",
    "benzene", "벤젠",
    "paraxylene", "para-xylene", "px", "파라자일렌",
    "meg", "monoethylene glycol", "에틸렌글리콜",
    "styrene", "스티렌",
    "butadiene", "부타디엔",
    "toluene", "톨루엔",
    "pe", "polyethylene", "폴리에틸렌",
    "hdpe", "high density polyethylene",
    "lldpe", "linear low density polyethylene",
    "pp", "polypropylene", "폴리프로필렌",
    "impact pp", "impact copolymer",
    "homo pp", "homopolymer pp",
]

# 뉴스 카테고리 키워드
NEWS_CATEGORIES = {
    "price": ["price", "pricing", "spot", "contract", "cost", "값", "가격", "단가"],
    "supply": ["supply", "production", "capacity", "output", "shortage", "공급", "생산", "설비"],
    "demand": ["demand", "consumption", "downstream", "import", "export", "수요", "소비", "수출", "수입"],
    "regulatory": ["regulation", "policy", "tariff", "sanction", "규제", "정책", "관세", "제재"],
    "ma": ["acquisition", "merger", "joint venture", "investment", "인수", "합병", "투자"],
}


class PetrochemNewsPlugin:
    """
    석유화학 산업 뉴스 수집 및 구조화 플러그인.

    RSS 피드에서 뉴스를 수집하고 화학물질별·카테고리별로 분류합니다.
    """

    def _parse_feed(self, url: str) -> list[dict]:
        """RSS 피드를 파싱합니다. feedparser 미설치 시 빈 리스트 반환."""
        if not _FEEDPARSER_AVAILABLE:
            return []
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "PetrochemBI/1.0"})
            return feed.entries if hasattr(feed, "entries") else []
        except Exception:
            return []

    def _extract_article_snippet(self, url: str, max_paragraphs: int = 3) -> str:
        """
        기사 URL에서 본문 첫 N개 단락을 추출합니다.
        403/429/타임아웃 발생 시 빈 문자열을 반환하여 파이프라인을 중단하지 않습니다.
        """
        if not _BS4_AVAILABLE:
            return ""
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PetrochemBI/1.0)"},
                timeout=8,
            )
            if resp.status_code in (403, 429):
                return ""
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
            return " ".join(paragraphs[:max_paragraphs])
        except Exception:
            return ""

    def _detect_chemicals(self, text: str) -> list[str]:
        """텍스트에서 언급된 화학물질 키워드를 추출합니다."""
        text_lower = text.lower()
        found = []
        for chem in TARGET_CHEMICALS:
            if chem in text_lower:
                # 약어는 단어 경계 체크
                if len(chem) <= 4:
                    if re.search(r'\b' + re.escape(chem) + r'\b', text_lower):
                        if chem not in found:
                            found.append(chem)
                else:
                    if chem not in found:
                        found.append(chem)
        return found

    def _detect_category(self, text: str) -> str:
        """뉴스 텍스트의 주요 카테고리를 판별합니다."""
        text_lower = text.lower()
        scores = {cat: 0 for cat in NEWS_CATEGORIES}
        for cat, keywords in NEWS_CATEGORIES.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[cat] += 1
        best = max(scores, key=lambda c: scores[c])
        return best if scores[best] > 0 else "general"

    @kernel_function(
        name="fetch_rss_news",
        description=(
            "ICIS, Chemical Week 등 석유화학 전문 RSS 피드에서 최신 뉴스를 수집합니다. "
            "화학물질 목록을 지정하면 관련 뉴스만 필터링합니다. "
            "결과는 JSON 문자열로 반환됩니다."
        ),
    )
    def fetch_rss_news(
        self,
        chemicals: Annotated[
            str,
            "조회할 화학물질 목록 (쉼표 구분 또는 JSON 배열). "
            "예: \"ethylene, propylene, PE\" 또는 비워두면 전체 수집",
        ] = "",
        max_per_feed: Annotated[int, "피드당 최대 수집 기사 수 (기본값: 10)"] = 10,
    ) -> str:
        """RSS 피드에서 석유화학 관련 뉴스를 수집하고 JSON으로 반환합니다."""
        if not _FEEDPARSER_AVAILABLE:
            return json.dumps({
                "error": "feedparser 패키지가 설치되지 않았습니다. pip install feedparser 를 실행하세요.",
                "items": [],
            }, ensure_ascii=False)

        # 필터 화학물질 파싱
        filter_chems: list[str] = []
        if chemicals.strip():
            try:
                parsed = json.loads(chemicals)
                filter_chems = [c.strip().lower() for c in parsed] if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                filter_chems = [c.strip().lower() for c in chemicals.split(",") if c.strip()]

        collected: list[dict] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for source_name, feed_url in PETROCHEM_RSS_FEEDS.items():
            entries = self._parse_feed(feed_url)
            count = 0
            for entry in entries:
                if count >= max_per_feed:
                    break
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                link = getattr(entry, "link", "")
                published = getattr(entry, "published", "") or getattr(entry, "updated", "")

                full_text = f"{title} {summary}"
                detected = self._detect_chemicals(full_text)

                # 필터 적용
                if filter_chems:
                    if not any(fc in detected or fc in full_text.lower() for fc in filter_chems):
                        continue

                category = self._detect_category(full_text)
                collected.append({
                    "source": source_name,
                    "title": title,
                    "url": link,
                    "published": published,
                    "snippet": summary[:300] if summary else "",
                    "chemicals_mentioned": detected,
                    "category": category,
                })
                count += 1

        result = {
            "fetched_at": timestamp,
            "total_count": len(collected),
            "items": collected,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @kernel_function(
        name="search_industry_news",
        description=(
            "석유화학 특화 검색 쿼리로 최신 산업 뉴스를 검색합니다. "
            "화학물질명과 시장 키워드를 조합하여 검색합니다. "
            "WebSearchPlugin.search_news에 위임합니다."
        ),
    )
    def search_industry_news(
        self,
        chemical: Annotated[str, "조회할 화학물질명. 예: ethylene, PP, MEG"],
        topic: Annotated[
            str,
            "검색 주제. 예: price, supply, demand, market outlook (기본값: market)",
        ] = "market",
        region: Annotated[str, "지역. 예: Asia, China, Europe, Global (기본값: Asia)"] = "Asia",
        max_results: Annotated[int, "최대 결과 수 (기본값: 5)"] = 5,
    ) -> str:
        """석유화학 도메인에 특화된 뉴스 검색 쿼리를 구성하여 검색합니다."""
        query = f"{chemical} {topic} {region} petrochemical 2025"
        try:
            from plugins.web_search_plugin import WebSearchPlugin
            searcher = WebSearchPlugin()
            return searcher.search_news(query=query, max_results=max_results, market="en-US")
        except ImportError:
            return f"WebSearchPlugin을 가져올 수 없습니다. 검색 쿼리: {query}"
        except Exception as e:
            return f"검색 중 오류: {str(e)}. 쿼리: {query}"

    @kernel_function(
        name="categorize_and_summarize",
        description=(
            "fetch_rss_news의 JSON 결과를 화학물질별·카테고리별로 구조화하여 "
            "마크다운 요약 텍스트로 반환합니다. "
            "뉴스 에이전트의 최종 출력 단계에 사용합니다."
        ),
    )
    def categorize_and_summarize(
        self,
        raw_news_json: Annotated[str, "fetch_rss_news가 반환한 JSON 문자열"],
        language: Annotated[str, "출력 언어: ko (한국어) 또는 en (영어), 기본값: ko"] = "ko",
    ) -> str:
        """뉴스 JSON을 화학물질×카테고리 매트릭스로 구조화하여 마크다운 반환."""
        try:
            data = json.loads(raw_news_json)
        except json.JSONDecodeError:
            return f"JSON 파싱 오류. 입력값: {raw_news_json[:200]}"

        items = data.get("items", [])
        if not items:
            msg = "수집된 뉴스가 없습니다." if language == "ko" else "No news items collected."
            return msg

        # 화학물질별 분류
        chem_map: dict[str, dict[str, list[str]]] = {}
        uncategorized: list[str] = []

        for item in items:
            chems = item.get("chemicals_mentioned", [])
            cat = item.get("category", "general")
            title = item.get("title", "")
            url = item.get("url", "")
            source = item.get("source", "")
            entry_text = f"- [{title}]({url}) *({source})*"

            if not chems:
                uncategorized.append(entry_text)
            else:
                for chem in chems:
                    if chem not in chem_map:
                        chem_map[chem] = {}
                    if cat not in chem_map[chem]:
                        chem_map[chem][cat] = []
                    if entry_text not in chem_map[chem][cat]:
                        chem_map[chem][cat].append(entry_text)

        fetched_at = data.get("fetched_at", "")
        lines = []
        if language == "ko":
            lines.append(f"## 석유화학 뉴스 요약 ({fetched_at})\n")
            lines.append(f"총 {len(items)}건 수집\n")
            cat_labels = {
                "price": "가격", "supply": "공급/생산", "demand": "수요",
                "regulatory": "규제/정책", "ma": "M&A/투자", "general": "일반",
            }
        else:
            lines.append(f"## Petrochemical News Summary ({fetched_at})\n")
            lines.append(f"Total {len(items)} articles collected\n")
            cat_labels = {
                "price": "Price", "supply": "Supply/Production", "demand": "Demand",
                "regulatory": "Regulatory", "ma": "M&A/Investment", "general": "General",
            }

        for chem, cat_dict in sorted(chem_map.items()):
            lines.append(f"\n### {chem.upper()}")
            for cat, entries in cat_dict.items():
                label = cat_labels.get(cat, cat)
                lines.append(f"\n**{label}**")
                lines.extend(entries)

        if uncategorized:
            header = "### 기타" if language == "ko" else "### Other"
            lines.append(f"\n{header}")
            lines.extend(uncategorized)

        return "\n".join(lines)
