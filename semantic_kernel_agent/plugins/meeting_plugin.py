"""
고객 미팅(Meeting) 플러그인

고객 미팅 이력 조회, 예정 미팅 확인, 미팅 요약 등의 기능을 제공합니다.
실제 환경에서는 Microsoft Graph API, Outlook Calendar, CRM 연동.
"""

from datetime import datetime
from semantic_kernel.functions import kernel_function


# ── 샘플 미팅 데이터 ──────────────────────────────────────────────────────────
_MEETINGS: list[dict] = [
    {
        "id": "MTG001",
        "account_id": "ACC001",
        "company": "삼성전자",
        "date": "2024-03-15",
        "type": "기술 데모",
        "attendees": ["김철수(고객)", "박세훈(SE)", "이지연(Sales)"],
        "agenda": "Azure OpenAI Service 기술 데모 및 PoC 범위 협의",
        "outcome": "PoC 진행 합의. 4월 중 환경 구성 후 2개월 PoC 진행 예정",
        "next_action": "PoC 제안서 발송 (이지연, 3/22까지)",
        "sentiment": "Positive",
        "deal_stage": "PoC",
    },
    {
        "id": "MTG002",
        "account_id": "ACC001",
        "company": "삼성전자",
        "date": "2024-04-02",
        "type": "PoC 킥오프",
        "attendees": ["김철수(고객)", "이승민(고객 IT)", "박세훈(SE)", "이지연(Sales)"],
        "agenda": "Azure ML + OpenAI PoC 환경 구성 및 일정 확정",
        "outcome": "PoC 환경 구성 완료. 모델 학습 파이프라인 1차 구현 시작",
        "next_action": "2주 후 중간 점검 미팅 (5/2 예정)",
        "sentiment": "Very Positive",
        "deal_stage": "PoC",
    },
    {
        "id": "MTG003",
        "account_id": "ACC002",
        "company": "LG화학",
        "date": "2024-03-20",
        "type": "니즈 발굴",
        "attendees": ["이영희(고객)", "정대한(고객 DT팀)", "최승준(Sales)"],
        "agenda": "배터리 생산 공정 AI 적용 가능성 탐색",
        "outcome": "이상 탐지 및 수율 예측 모델에 높은 관심. 기존 데이터 품질 이슈 존재",
        "next_action": "데이터 현황 파악 후 아키텍처 제안서 작성 (4/5까지)",
        "sentiment": "Positive",
        "deal_stage": "Discovery",
    },
    {
        "id": "MTG004",
        "account_id": "ACC004",
        "company": "현대자동차",
        "date": "2024-03-28",
        "type": "경쟁 대응",
        "attendees": ["최민준(고객)", "김태영(고객 AI팀장)", "이지연(Sales)", "윤상욱(SA)"],
        "agenda": "경쟁사 AWS SageMaker 대비 Azure ML 우위 설명",
        "outcome": "경쟁사와 병행 검토 중임을 확인. 가격 및 지원 조건이 주요 결정 요인",
        "next_action": "맞춤형 상업 제안서 제출 (4/10까지), Executive Meeting 추진",
        "sentiment": "Neutral",
        "deal_stage": "Negotiation",
    },
    {
        "id": "MTG005",
        "account_id": "ACC005",
        "company": "신한금융그룹",
        "date": "2024-04-01",
        "type": "비즈니스 리뷰",
        "attendees": ["정수진(고객)", "박현우(고객 CISO)", "최승준(Sales)"],
        "agenda": "FDS AI 모델 성능 리뷰 및 추가 도입 방향 논의",
        "outcome": "현재 Azure OpenAI 기반 FDS 성능 만족. Copilot M365 추가 도입 검토",
        "next_action": "Copilot M365 데모 세션 일정 조율 (4/15 예정)",
        "sentiment": "Very Positive",
        "deal_stage": "Expansion",
    },
    {
        "id": "MTG006",
        "account_id": "ACC003",
        "company": "카카오",
        "date": "2024-04-10",
        "type": "기술 워크숍",
        "attendees": ["박지민(고객)", "이현수(고객 ML팀)", "박세훈(SE)"],
        "agenda": "Semantic Kernel + Azure AI Search 기반 RAG 구현 워크숍",
        "outcome": "기술 적합성 확인. 자체 개발 대비 Azure 관리형 서비스 장점 인식",
        "next_action": "아키텍처 설계 문서 공유 후 PoC 계획 수립",
        "sentiment": "Positive",
        "deal_stage": "PoC",
    },
    {
        "id": "MTG007",
        "account_id": "ACC001",
        "company": "삼성전자",
        "date": "2024-05-02",
        "type": "중간 점검",
        "attendees": ["김철수(고객)", "박세훈(SE)", "이지연(Sales)"],
        "agenda": "PoC 중간 점검 - 모델 성능 및 일정 리뷰",
        "outcome": "모델 정확도 87% 달성 (목표 85% 초과). 최종 발표 준비",
        "next_action": "6/1 PoC 최종 결과 발표 준비",
        "sentiment": "Very Positive",
        "deal_stage": "PoC",
    },
]


class MeetingPlugin:
    """고객 미팅 조회 및 관리 플러그인"""

    @kernel_function(
        name="get_meetings_by_account",
        description="특정 고객사의 미팅 이력을 조회합니다. 고객 ID(예: ACC001) 또는 회사명(예: '삼성전자')으로 검색합니다.",
    )
    def get_meetings_by_account(self, account_identifier: str) -> str:
        """특정 고객사의 전체 미팅 이력을 반환합니다"""
        identifier_lower = account_identifier.lower()
        matches = [
            m for m in _MEETINGS
            if m["account_id"].lower() == identifier_lower
            or identifier_lower in m["company"].lower()
        ]

        if not matches:
            return f"'{account_identifier}'의 미팅 이력이 없습니다."

        matches_sorted = sorted(matches, key=lambda x: x["date"], reverse=True)
        lines = [f"[{matches[0]['company']} 미팅 이력 - {len(matches)}건]"]
        for m in matches_sorted:
            lines.append(
                f"\n[{m['id']}] {m['date']} | {m['type']} | 감성: {m['sentiment']}\n"
                f"  참석: {', '.join(m['attendees'])}\n"
                f"  안건: {m['agenda']}\n"
                f"  결과: {m['outcome']}\n"
                f"  다음 액션: {m['next_action']}\n"
                f"  딜 단계: {m['deal_stage']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_recent_meetings",
        description="최근 N개의 미팅 이력을 조회합니다. 전체 고객의 최신 미팅 활동을 파악할 때 사용합니다. count는 조회할 미팅 수(기본값: 5).",
    )
    def get_recent_meetings(self, count: int = 5) -> str:
        """최근 미팅 이력을 반환합니다"""
        sorted_meetings = sorted(_MEETINGS, key=lambda x: x["date"], reverse=True)
        recent = sorted_meetings[:count]

        lines = [f"[최근 {len(recent)}개 미팅]"]
        for m in recent:
            lines.append(
                f"\n{m['date']} | [{m['id']}] {m['company']} - {m['type']}\n"
                f"  결과: {m['outcome'][:80]}...\n"
                f"  다음 액션: {m['next_action']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_pending_actions",
        description="완료되지 않은 미팅 후속 액션(Next Action)을 조회합니다. 팔로업이 필요한 항목을 확인할 때 사용합니다.",
    )
    def get_pending_actions(self) -> str:
        """팔로업이 필요한 다음 액션 목록을 반환합니다"""
        # 간단히 미래 날짜 또는 최근 30일 내 next_action이 있는 미팅 반환
        lines = ["[팔로업 필요 액션 목록]"]
        for m in sorted(_MEETINGS, key=lambda x: x["date"], reverse=True):
            if m["next_action"]:
                lines.append(
                    f"  [{m['id']}] {m['company']} ({m['date']})\n"
                    f"    → {m['next_action']}\n"
                    f"    딜 단계: {m['deal_stage']} | 감성: {m['sentiment']}"
                )
        return "\n".join(lines) if len(lines) > 1 else "팔로업 필요 액션이 없습니다."

    @kernel_function(
        name="get_meetings_by_deal_stage",
        description="딜 단계별 미팅 현황을 조회합니다. stage 파라미터에 딜 단계를 입력하세요. 유효값: Discovery, PoC, Negotiation, Expansion",
    )
    def get_meetings_by_deal_stage(self, stage: str) -> str:
        """딜 단계별 미팅 현황을 반환합니다"""
        matches = [m for m in _MEETINGS if m["deal_stage"].lower() == stage.lower()]

        if not matches:
            stages = list({m["deal_stage"] for m in _MEETINGS})
            return f"'{stage}' 단계의 미팅이 없습니다. 현재 단계: {', '.join(stages)}"

        lines = [f"[딜 단계: {stage} - {len(matches)}건]"]
        for m in sorted(matches, key=lambda x: x["date"], reverse=True):
            lines.append(
                f"\n  {m['date']} | {m['company']} | {m['type']}\n"
                f"  결과: {m['outcome']}\n"
                f"  감성: {m['sentiment']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_meeting_summary_stats",
        description="전체 미팅 현황 통계를 요약합니다. 미팅 수, 딜 단계별 분포, 감성 분포 등을 반환합니다.",
    )
    def get_meeting_summary_stats(self) -> str:
        """미팅 현황 통계 요약을 반환합니다"""
        total = len(_MEETINGS)

        stage_counts: dict[str, int] = {}
        sentiment_counts: dict[str, int] = {}
        company_counts: dict[str, int] = {}

        for m in _MEETINGS:
            stage_counts[m["deal_stage"]] = stage_counts.get(m["deal_stage"], 0) + 1
            sentiment_counts[m["sentiment"]] = sentiment_counts.get(m["sentiment"], 0) + 1
            company_counts[m["company"]] = company_counts.get(m["company"], 0) + 1

        stage_str = ", ".join(f"{k}: {v}건" for k, v in sorted(stage_counts.items()))
        sentiment_str = ", ".join(f"{k}: {v}건" for k, v in sorted(sentiment_counts.items()))
        top_company = max(company_counts.items(), key=lambda x: x[1])

        return (
            f"[미팅 현황 통계]\n"
            f"- 총 미팅 수: {total}건\n"
            f"- 딜 단계별: {stage_str}\n"
            f"- 고객 감성: {sentiment_str}\n"
            f"- 가장 많은 미팅: {top_company[0]} ({top_company[1]}회)\n"
            f"- 최근 미팅: {max(_MEETINGS, key=lambda x: x['date'])['date']}"
        )
