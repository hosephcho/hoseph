"""
06. 석유화학 Business Intelligence Agent

S&P Global/Platts, ICIS 등 전문 기관의 뉴스와 시장 가격 데이터를
자동으로 수집·분석·요약하여 일간/주간 BI 보고서를 생성합니다.

에이전트 파이프라인:
  NewsAgent → PriceAgent → ReportAgent

사용법:
  python semantic_kernel_agent/06_petrochem_bi_agent.py --report-type daily
  python semantic_kernel_agent/06_petrochem_bi_agent.py --report-type weekly
  python semantic_kernel_agent/06_petrochem_bi_agent.py --test
"""

import argparse
import asyncio
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
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext

from config.settings import get_azure_openai_config, get_petrochem_config
from plugins.web_search_plugin import WebSearchPlugin
from plugins.data_analysis_plugin import DataAnalysisPlugin
from plugins.petrochem_news_plugin import PetrochemNewsPlugin, TARGET_CHEMICALS
from plugins.market_price_plugin import MarketPricePlugin
from plugins.report_generator_plugin import ReportGeneratorPlugin
from utils.query_history import QueryHistory


# ---------------------------------------------------------------------------
# 시스템 프롬프트
# ---------------------------------------------------------------------------

_NEWS_AGENT_PROMPT = """당신은 석유화학 산업 뉴스 수집 전문 에이전트입니다.

역할:
- S&P Global, Platts, ICIS, Chemical Week 등 전문 기관의 뉴스를 수집합니다.
- 에틸렌, 프로필렌, 벤젠, PX, MEG, 스티렌, PE, HDPE, LLDPE, PP, Impact PP, Homo PP,
  부타디엔, 톨루엔 등 주요 석유화학 화학물질 관련 뉴스를 필터링합니다.
- 뉴스를 가격/공급/수요/규제/M&A 카테고리로 분류합니다.

도구 활용 가이드:
1. fetch_rss_news: RSS 피드에서 최신 뉴스 수집 (주요 화학물질 전달)
2. search_industry_news: 특정 화학물질의 심층 뉴스 검색
3. categorize_and_summarize: 수집된 뉴스를 구조화된 마크다운으로 변환

출력 형식:
- 화학물질별 뉴스 요약 (마크다운)
- 각 뉴스에 출처 URL 포함
- 한국어로 작성
"""

_PRICE_AGENT_PROMPT = """당신은 석유화학 시장 가격 분석 전문 에이전트입니다.

역할:
- 에틸렌, 프로필렌, 벤젠, PX, MEG, PE, HDPE, LLDPE, PP 등의 현물 가격을 수집합니다.
- Asia CFR/FOB 기준 USD/ton 가격을 수집하고 과거 데이터와 비교합니다.
- 가격 트렌드(상승/하락/보합)와 변동 폭을 분석합니다.

도구 활용 가이드:
1. get_price_snapshot: 여러 화학물질의 현재 가격 수집 및 캐시 저장
2. compute_price_change: 특정 화학물질의 기간 대비 가격 변동 분석
3. get_price_summary_table: 전체 가격 요약 마크다운 테이블 생성

출력 형식:
- 화학물질별 가격 테이블 (마크다운)
- 주요 가격 변동 하이라이트
- 한국어로 작성
"""

_REPORT_AGENT_PROMPT = """당신은 석유화학 시장 BI 보고서 작성 전문 에이전트입니다.

역할:
- 뉴스 에이전트와 가격 에이전트의 분석 결과를 종합하여 경영진용 BI 보고서를 작성합니다.
- 한국어 보고서와 영어 보고서를 모두 작성합니다.
- 보고서를 파일로 저장합니다.

보고서 구조 (반드시 포함):
1. Executive Summary (핵심 요약) - 3~5개 bullet point
2. 화학물질별 가격 동향 (Price Trends)
3. 주요 시장 뉴스 (Market News by Chemical)
4. 수급 전망 (Supply/Demand Outlook)
5. 리스크 및 기회 요인 (Key Risks & Opportunities)

도구 활용 가이드:
1. save_markdown_report: 한국어·영어 보고서를 마크다운 파일로 저장
2. save_json_summary: 기계 가독형 JSON 요약 파일 저장
3. upload_to_azure_blob: Azure Blob에 업로드 (선택, 설정된 경우)

응답 형식:
- [한국어 보고서 시작] ~ [한국어 보고서 끝] 구분자 사용
- [영어 보고서 시작] ~ [영어 보고서 끝] 구분자 사용
- 마지막에 반드시 save_markdown_report 도구를 호출하여 파일로 저장
"""


# ---------------------------------------------------------------------------
# 에이전트 헬퍼 (04_multi_agent.py 패턴 재사용)
# ---------------------------------------------------------------------------

def create_agent(
    kernel: sk.Kernel,
    role: str,
    system_prompt: str,
    tools: list[str] | None = None,
    max_tokens: int = 2000,
) -> tuple[ChatHistory, OpenAIChatPromptExecutionSettings]:
    history = ChatHistory()
    history.add_system_message(system_prompt)

    if tools:
        settings = OpenAIChatPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                filters={"included_plugins": tools}
            ),
            max_tokens=max_tokens,
            temperature=0.3,
        )
    else:
        settings = OpenAIChatPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),
            max_tokens=max_tokens,
            temperature=0.4,
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
    print(f"[{agent_name}] 완료 ({len(result)} chars)")
    return result


# ---------------------------------------------------------------------------
# 커널 빌드
# ---------------------------------------------------------------------------

def build_kernel(config) -> tuple[sk.Kernel, AzureChatCompletion]:
    kernel = sk.Kernel()

    chat_service = AzureChatCompletion(
        deployment_name=config.deployment_name,
        endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
        service_id="azure_chat",
    )
    kernel.add_service(chat_service)

    # 기존 플러그인 (공유)
    kernel.add_plugin(WebSearchPlugin(), plugin_name="Search")
    kernel.add_plugin(DataAnalysisPlugin(), plugin_name="DataAnalysis")

    # 신규 석유화학 플러그인
    kernel.add_plugin(PetrochemNewsPlugin(), plugin_name="PetrochemNews")
    kernel.add_plugin(MarketPricePlugin(), plugin_name="MarketPrice")
    kernel.add_plugin(ReportGeneratorPlugin(), plugin_name="ReportGenerator")

    return kernel, chat_service


# ---------------------------------------------------------------------------
# 메인 파이프라인
# ---------------------------------------------------------------------------

async def run_bi_pipeline(report_type: str = "daily", test_mode: bool = False):
    """
    석유화학 BI 파이프라인 실행.

    NewsAgent → PriceAgent → ReportAgent 순으로 실행하고
    최종 보고서를 파일로 저장합니다.
    """
    print("=" * 60)
    print(f"  석유화학 BI Agent 파이프라인 ({report_type.upper()})")
    print("=" * 60)

    config = get_azure_openai_config()
    petrochem_cfg = get_petrochem_config()
    kernel, chat_service = build_kernel(config)

    query_history = QueryHistory(
        persist_path=os.path.join(
            os.path.dirname(__file__), "..", ".petrochem_query_history.json"
        )
    )

    # 분석 대상 화학물질 (테스트 모드에서는 범위 축소)
    if test_mode:
        target_chems = ["ethylene", "PP", "MEG"]
        period_label = "최근 24시간 (테스트)"
        news_task_prefix = "테스트 모드: "
    else:
        target_chems = [
            "ethylene", "propylene", "benzene", "PX", "MEG",
            "PE", "HDPE", "LLDPE", "PP", "Homo PP", "Impact PP",
        ]
        period_label = "최근 1주일" if report_type == "weekly" else "최근 24시간"
        news_task_prefix = ""

    chems_str = ", ".join(target_chems)
    print(f"\n  대상 화학물질: {chems_str}")
    print(f"  분석 기간: {period_label}")
    print(f"  출력 디렉토리: {petrochem_cfg['output_dir']}\n")

    # --- 에이전트 생성 ---
    print("에이전트 초기화 중...\n")

    news_history, news_settings = create_agent(
        kernel, role="NewsAgent",
        system_prompt=_NEWS_AGENT_PROMPT,
        tools=["PetrochemNews", "Search"],
        max_tokens=3000,
    )
    price_history, price_settings = create_agent(
        kernel, role="PriceAgent",
        system_prompt=_PRICE_AGENT_PROMPT,
        tools=["MarketPrice", "DataAnalysis", "Search"],
        max_tokens=2000,
    )
    report_history, report_settings = create_agent(
        kernel, role="ReportAgent",
        system_prompt=_REPORT_AGENT_PROMPT,
        tools=["ReportGenerator"],
        max_tokens=4000,
    )

    print("\n파이프라인 실행 시작")
    print("=" * 60)

    # === Step 1: 뉴스 수집 ===
    news_result = await run_agent(
        kernel, chat_service,
        agent_name="NewsAgent",
        history=news_history,
        settings=news_settings,
        task=(
            f"{news_task_prefix}"
            f"다음 화학물질들의 {period_label} 석유화학 뉴스를 수집하고 "
            f"카테고리(가격/공급/수요/규제/M&A)별로 구조화해줘:\n"
            f"{chems_str}\n\n"
            f"1. fetch_rss_news로 RSS 피드 수집\n"
            f"2. 주요 화학물질별 search_industry_news로 보완 검색\n"
            f"3. categorize_and_summarize로 결과 구조화\n"
            f"결과는 화학물질별 마크다운 요약으로 반환해줘."
        ),
        query_history=query_history,
    )

    # === Step 2: 가격 분석 ===
    price_result = await run_agent(
        kernel, chat_service,
        agent_name="PriceAgent",
        history=price_history,
        settings=price_settings,
        task=(
            f"다음 화학물질들의 현재 시장 가격을 수집하고 트렌드를 분석해줘:\n"
            f"{chems_str}\n\n"
            f"1. get_price_snapshot으로 현재 가격 수집 (JSON 배열 전달)\n"
            f"2. compute_price_change로 주요 화학물질의 가격 변동 분석\n"
            f"3. get_price_summary_table로 전체 가격 요약 테이블 생성\n\n"
            f"아래는 뉴스 요약 컨텍스트입니다 (가격 언급 참고용):\n"
            f"{news_result[:1500]}"
        ),
        query_history=query_history,
    )

    # === Step 3: 보고서 작성 ===
    type_label_ko = "일간" if report_type == "daily" else "주간"
    final_report = await run_agent(
        kernel, chat_service,
        agent_name="ReportAgent",
        history=report_history,
        settings=report_settings,
        task=(
            f"아래 수집 결과를 바탕으로 석유화학 시장 {type_label_ko} BI 보고서를 작성하고 "
            f"파일로 저장해줘.\n\n"
            f"## 뉴스 수집 결과 (NewsAgent):\n{news_result[:2000]}\n\n"
            f"## 가격 분석 결과 (PriceAgent):\n{price_result[:2000]}\n\n"
            f"한국어 보고서와 영어 보고서를 모두 작성하고, "
            f"save_markdown_report 도구로 저장해줘. "
            f"report_type='{report_type}'"
        ),
        query_history=query_history,
    )

    print("\n" + "=" * 60)
    print("=== 파이프라인 완료 ===")
    print("=" * 60)
    print(final_report[:1000])
    if len(final_report) > 1000:
        print(f"... (총 {len(final_report)} chars)")

    query_history.display()
    return final_report


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="석유화학 Business Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python 06_petrochem_bi_agent.py --report-type daily
  python 06_petrochem_bi_agent.py --report-type weekly
  python 06_petrochem_bi_agent.py --test
        """,
    )
    parser.add_argument(
        "--report-type",
        choices=["daily", "weekly"],
        default="daily",
        help="보고서 유형 (기본값: daily)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="테스트 모드: 소수 화학물질로 파이프라인 검증",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_bi_pipeline(report_type=args.report_type, test_mode=args.test))
