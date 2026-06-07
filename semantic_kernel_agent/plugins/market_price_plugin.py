"""
석유화학 시장 가격 플러그인

현물 가격 데이터를 웹 검색으로 수집하고 시계열 캐시에 저장하여
가격 트렌드를 분석합니다.

데이터 소스 전략:
  - MVP (무료): 웹 검색 결과 스니펫에서 가격 수치 정규식 추출
  - Phase 1.5 (유료): SPGLOBAL_API_KEY 또는 ICIS_API_KEY 설정 시 공식 API 사용

캐시 구조:
  data/price_cache/{chemical}.json  ← 롤링 시계열 배열
  [{"date": "2025-06-07", "price": 850.0, "unit": "USD/ton", "region": "Asia", "source": "web"}, ...]
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from semantic_kernel.functions import kernel_function

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 캐시 디렉토리 (환경변수 > 기본값)
_DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "price_cache",
)
PRICE_CACHE_DIR = os.environ.get("PETROCHEM_PRICE_CACHE_DIR", _DEFAULT_CACHE_DIR)

# 가격 추출 정규식: "$850", "850 USD/ton", "USD 1,050/mt" 등
_PRICE_PATTERN = re.compile(
    r'(?:USD\s*|US\$\s*|\$\s*)?(\d{2,4}(?:[,\.]\d{3})?(?:\.\d+)?)'
    r'\s*(?:USD\s*)?(?:/\s*(?:mt|ton|tonne|metric\s*ton))',
    re.IGNORECASE,
)

# 화학물질별 웹 검색 쿼리 템플릿
_PRICE_QUERY_TEMPLATES = {
    "ethylene": "ethylene spot price Asia CFR USD per metric ton today",
    "propylene": "propylene spot price Asia CFR USD per ton current",
    "benzene": "benzene spot price Asia FOB USD per ton",
    "paraxylene": "paraxylene PX spot price Asia CFR USD per ton",
    "px": "paraxylene PX spot price Asia CFR USD per ton",
    "meg": "MEG monoethylene glycol spot price China CFR USD per ton",
    "styrene": "styrene spot price Asia CFR USD per ton",
    "butadiene": "butadiene spot price Asia USD per ton",
    "toluene": "toluene spot price Asia USD per ton",
    "pe": "polyethylene PE spot price Asia USD per ton",
    "hdpe": "HDPE high density polyethylene price Asia USD per ton",
    "lldpe": "LLDPE linear low density polyethylene price Asia USD per ton",
    "pp": "polypropylene PP spot price Asia USD per ton",
    "homo pp": "homo polypropylene PP price Asia USD per ton",
    "impact pp": "impact copolymer PP price Asia USD per ton",
}


def _safe_chemical_filename(chemical: str) -> str:
    """화학물질명을 파일명으로 안전하게 변환합니다."""
    return re.sub(r'[^a-z0-9_]', '_', chemical.lower().strip())


def _load_cache(chemical: str) -> list[dict]:
    """캐시 파일을 로드합니다. 없으면 빈 리스트 반환."""
    fname = os.path.join(PRICE_CACHE_DIR, f"{_safe_chemical_filename(chemical)}.json")
    if not os.path.exists(fname):
        return []
    try:
        with open(fname, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_cache(chemical: str, records: list[dict], max_records: int = 365) -> None:
    """캐시 파일에 저장합니다. max_records 초과분은 오래된 것부터 제거."""
    os.makedirs(PRICE_CACHE_DIR, exist_ok=True)
    records = records[-max_records:]  # 최근 N개만 유지
    fname = os.path.join(PRICE_CACHE_DIR, f"{_safe_chemical_filename(chemical)}.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


class MarketPricePlugin:
    """
    석유화학 시장 가격 수집 및 트렌드 분석 플러그인.

    웹 검색 기반으로 가격 스냅샷을 수집하고, 로컬 캐시에 시계열로 저장하여
    DataAnalysisPlugin을 활용한 트렌드 분석을 제공합니다.
    """

    def _extract_price_from_text(self, text: str) -> float | None:
        """텍스트에서 첫 번째 유효한 USD/ton 가격을 추출합니다."""
        matches = _PRICE_PATTERN.findall(text)
        for m in matches:
            try:
                val = float(m.replace(",", ""))
                if 100 <= val <= 5000:  # 합리적인 석유화학 가격 범위
                    return val
            except ValueError:
                continue
        return None

    def _search_price(self, chemical: str) -> dict:
        """웹 검색으로 가격 정보를 수집합니다."""
        query = _PRICE_QUERY_TEMPLATES.get(
            chemical.lower(),
            f"{chemical} spot price Asia USD per metric ton current",
        )
        try:
            from plugins.web_search_plugin import WebSearchPlugin
            searcher = WebSearchPlugin()
            raw = searcher.search(query=query, max_results=5, market="en-US")
            price = self._extract_price_from_text(raw)
            return {
                "chemical": chemical,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "price": price,
                "unit": "USD/ton",
                "region": "Asia",
                "source": "web_search",
                "query_used": query,
                "raw_snippet": raw[:500] if raw else "",
            }
        except Exception as e:
            return {
                "chemical": chemical,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "price": None,
                "unit": "USD/ton",
                "region": "Asia",
                "source": "web_search",
                "error": str(e),
            }

    @kernel_function(
        name="get_price_snapshot",
        description=(
            "지정된 석유화학 화학물질들의 현재 현물 가격 스냅샷을 수집합니다. "
            "웹 검색으로 가격 데이터를 수집하고 로컬 캐시에 저장합니다. "
            "결과는 JSON 문자열로 반환됩니다."
        ),
    )
    def get_price_snapshot(
        self,
        chemicals_json: Annotated[
            str,
            "조회할 화학물질 목록. JSON 배열 또는 쉼표 구분 문자열. "
            "예: '[\"ethylene\", \"propylene\", \"PE\"]' 또는 \"ethylene, PP, MEG\"",
        ],
    ) -> str:
        """화학물질 목록의 현재 가격을 수집하고 JSON으로 반환합니다."""
        try:
            chemicals = json.loads(chemicals_json)
            if not isinstance(chemicals, list):
                chemicals = [str(chemicals)]
        except json.JSONDecodeError:
            chemicals = [c.strip() for c in chemicals_json.split(",") if c.strip()]

        snapshots = []
        for chem in chemicals:
            snap = self._search_price(chem)
            snapshots.append(snap)

            # 가격을 추출했으면 캐시에 저장
            if snap.get("price") is not None:
                records = _load_cache(chem)
                # 오늘 날짜 중복 방지
                today = snap["date"]
                records = [r for r in records if r.get("date") != today]
                records.append({k: v for k, v in snap.items() if k not in ("raw_snippet", "query_used", "error")})
                _save_cache(chem, records)

        result = {
            "snapshot_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(snapshots),
            "snapshots": snapshots,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @kernel_function(
        name="load_price_history",
        description=(
            "로컬 캐시에서 화학물질의 과거 가격 시계열 데이터를 불러옵니다. "
            "DataAnalysisPlugin의 통계 분석 입력으로 사용할 수 있습니다."
        ),
    )
    def load_price_history(
        self,
        chemical: Annotated[str, "화학물질명. 예: ethylene, PP, MEG"],
        days: Annotated[int, "조회할 과거 일수 (기본값: 30)"] = 30,
    ) -> str:
        """캐시에서 가격 히스토리를 로드합니다."""
        records = _load_cache(chemical)
        if not records:
            return f"{chemical} 가격 캐시가 없습니다. get_price_snapshot을 먼저 실행하세요."

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered = [r for r in records if r.get("date", "") >= cutoff and r.get("price") is not None]

        if not filtered:
            return f"{chemical}: 최근 {days}일 이내 캐시 데이터가 없습니다."

        lines = [f"# {chemical.upper()} 가격 이력 (최근 {days}일, {len(filtered)}건)"]
        lines.append("날짜,가격(USD/ton),지역")
        for r in filtered:
            lines.append(f"{r['date']},{r['price']},{r.get('region', 'Asia')}")

        # DataAnalysisPlugin용 숫자 배열도 추가
        prices = [str(r["price"]) for r in filtered]
        lines.append(f"\n# 가격 배열 (분석용): {', '.join(prices)}")
        return "\n".join(lines)

    @kernel_function(
        name="compute_price_change",
        description=(
            "캐시된 가격 데이터를 분석하여 기간 대비 가격 변동률과 트렌드를 반환합니다. "
            "DataAnalysisPlugin을 내부적으로 활용합니다."
        ),
    )
    def compute_price_change(
        self,
        chemical: Annotated[str, "화학물질명"],
        window_days: Annotated[int, "비교 기간(일). 예: 7 → 최근 7일 vs 이전 7일 비교"] = 7,
    ) -> str:
        """가격 변동 분석 결과를 반환합니다."""
        records = _load_cache(chemical)
        valid = [r for r in records if r.get("price") is not None]

        if len(valid) < 2:
            return json.dumps({
                "chemical": chemical,
                "error": f"분석에 필요한 데이터가 부족합니다 (현재 {len(valid)}건, 최소 2건 필요)",
            }, ensure_ascii=False)

        # 최근 window_days와 이전 window_days 분리
        recent = valid[-window_days:] if len(valid) >= window_days else valid[len(valid) // 2:]
        previous = valid[:-len(recent)] if len(valid) > len(recent) else []

        recent_prices = [r["price"] for r in recent]
        previous_prices = [r["price"] for r in previous] if previous else []

        recent_avg = sum(recent_prices) / len(recent_prices)
        recent_min = min(recent_prices)
        recent_max = max(recent_prices)

        if previous_prices:
            prev_avg = sum(previous_prices) / len(previous_prices)
            pct_change = ((recent_avg - prev_avg) / prev_avg) * 100 if prev_avg else 0
            trend = "상승" if pct_change > 1 else ("하락" if pct_change < -1 else "보합")
        else:
            prev_avg = None
            pct_change = 0
            trend = "데이터 부족"

        result = {
            "chemical": chemical,
            "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "window_days": window_days,
            "recent_avg_usd_ton": round(recent_avg, 1),
            "recent_min": recent_min,
            "recent_max": recent_max,
            "previous_avg_usd_ton": round(prev_avg, 1) if prev_avg else None,
            "pct_change": round(pct_change, 2),
            "trend": trend,
            "data_points": len(valid),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @kernel_function(
        name="get_price_summary_table",
        description=(
            "여러 화학물질의 최신 캐시 가격을 한 번에 조회하여 "
            "마크다운 테이블 형식으로 반환합니다. 보고서 작성에 활용합니다."
        ),
    )
    def get_price_summary_table(
        self,
        chemicals_json: Annotated[
            str,
            "화학물질 목록 (JSON 배열 또는 쉼표 구분). 예: '[\"ethylene\",\"PP\",\"MEG\"]'",
        ],
        language: Annotated[str, "출력 언어: ko 또는 en (기본값: ko)"] = "ko",
    ) -> str:
        """화학물질 가격 요약 마크다운 테이블을 반환합니다."""
        try:
            chemicals = json.loads(chemicals_json)
            if not isinstance(chemicals, list):
                chemicals = [str(chemicals)]
        except json.JSONDecodeError:
            chemicals = [c.strip() for c in chemicals_json.split(",") if c.strip()]

        if language == "ko":
            header = "| 화학물질 | 최근 가격 (USD/ton) | 전일比 | 트렌드 | 업데이트 |"
            sep = "|---|---|---|---|---|"
        else:
            header = "| Chemical | Latest Price (USD/ton) | Change | Trend | Updated |"
            sep = "|---|---|---|---|---|"

        rows = [header, sep]
        for chem in chemicals:
            records = _load_cache(chem)
            valid = [r for r in records if r.get("price") is not None]
            if not valid:
                rows.append(f"| {chem.upper()} | N/A | - | - | - |")
                continue

            latest = valid[-1]
            price = latest["price"]
            date = latest.get("date", "")

            # 전일 대비
            if len(valid) >= 2:
                prev_price = valid[-2]["price"]
                diff = price - prev_price
                pct = (diff / prev_price * 100) if prev_price else 0
                change_str = f"{'+' if diff >= 0 else ''}{diff:.0f} ({pct:+.1f}%)"
                trend = "↑" if pct > 0.5 else ("↓" if pct < -0.5 else "→")
            else:
                change_str = "-"
                trend = "-"

            rows.append(f"| {chem.upper()} | {price:,.0f} | {change_str} | {trend} | {date} |")

        return "\n".join(rows)
