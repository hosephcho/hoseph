"""
마케팅 전략 수립(Marketing) 플러그인

고객 세그먼트 분석, 마케팅 전략 생성, 캠페인 조회, ROI 계산 기능을 제공합니다.
실제 환경에서는 Dynamics 365 Marketing, Adobe Marketo 등과 연동합니다.
"""

from semantic_kernel.functions import kernel_function


# ── 샘플 캠페인 데이터 ────────────────────────────────────────────────────────
_CAMPAIGNS: list[dict] = [
    {
        "id": "CAM001",
        "name": "Q2 2024 Enterprise AI 도입 캠페인",
        "type": "Outbound",
        "target_tier": "Enterprise",
        "target_industry": ["전자/반도체", "자동차/모빌리티"],
        "channels": ["이메일", "세미나", "1:1 미팅"],
        "budget": 50_000_000,
        "status": "Active",
        "start_date": "2024-04-01",
        "end_date": "2024-06-30",
        "leads_generated": 12,
        "meetings_booked": 5,
        "pipeline_value": 1_500_000_000,
        "key_message": "Azure AI로 제조 공정 혁신 - ROI 120% 달성 사례",
    },
    {
        "id": "CAM002",
        "name": "금융권 컴플라이언스 AI 캠페인",
        "type": "Account-Based",
        "target_tier": "Enterprise",
        "target_industry": ["금융/은행", "보험"],
        "channels": ["임원급 라운드테이블", "백서 배포", "웨비나"],
        "budget": 30_000_000,
        "status": "Active",
        "start_date": "2024-03-01",
        "end_date": "2024-05-31",
        "leads_generated": 8,
        "meetings_booked": 4,
        "pipeline_value": 2_000_000_000,
        "key_message": "금융감독원 가이드라인 준수 + Azure AI로 FDS/컴플라이언스 자동화",
    },
    {
        "id": "CAM003",
        "name": "스타트업/Mid-Market IT 플랫폼 육성",
        "type": "Digital",
        "target_tier": "Mid-Market",
        "target_industry": ["IT/플랫폼", "게임", "이커머스"],
        "channels": ["SNS 광고", "콘텐츠 마케팅", "온라인 웨비나"],
        "budget": 15_000_000,
        "status": "Active",
        "start_date": "2024-04-15",
        "end_date": "2024-07-15",
        "leads_generated": 35,
        "meetings_booked": 8,
        "pipeline_value": 500_000_000,
        "key_message": "Azure 스타트업 크레딧 + GPT-4 API로 빠르게 AI 제품 출시",
    },
    {
        "id": "CAM004",
        "name": "Copilot M365 생산성 혁신 캠페인",
        "type": "Cross-Sell",
        "target_tier": "Enterprise",
        "target_industry": ["전 산업군"],
        "channels": ["이메일", "인앱 배너", "세일즈 팀 활성화"],
        "budget": 20_000_000,
        "status": "Planning",
        "start_date": "2024-05-01",
        "end_date": "2024-08-31",
        "leads_generated": 0,
        "meetings_booked": 0,
        "pipeline_value": 0,
        "key_message": "AI로 업무 생산성 40% 향상 - Microsoft Copilot M365 도입 사례",
    },
]

# ── 마케팅 전략 템플릿 ─────────────────────────────────────────────────────────
_STRATEGY_TEMPLATES: dict[str, dict] = {
    "enterprise_ai_adoption": {
        "name": "엔터프라이즈 AI 도입 전략",
        "phases": [
            "1단계 (0-3개월): 임원급 비전 공유 세션 + ROI 케이스 스터디",
            "2단계 (3-6개월): 기술 워크숍 + PoC 지원 + 전담 SE 배정",
            "3단계 (6-12개월): PoC 결과 기반 본계약 + 확장 로드맵 수립",
        ],
        "key_tactics": ["임원 스폰서십 확보", "챔피언 육성", "성공 사례 내재화", "경쟁 대응 자료 준비"],
        "success_metrics": ["PoC 성공률", "임원 참여도", "파이프라인 규모", "딜 사이클 단축"],
    },
    "at_risk_retention": {
        "name": "이탈 위험 고객 리텐션 전략",
        "phases": [
            "1단계 (즉시): 임원급 긴급 미팅 + 불만 원인 파악",
            "2단계 (1-2개월): 전담 CSM 배정 + 맞춤형 지원 플랜 수립",
            "3단계 (2-4개월): 성과 개선 입증 + 계약 갱신 협상",
        ],
        "key_tactics": ["근본 원인 분석", "경영진 에스컬레이션", "가치 재정립", "경쟁사 차별화"],
        "success_metrics": ["건강 점수 회복", "계약 갱신율", "NPS 개선", "추가 도입 여부"],
    },
    "cross_sell_upsell": {
        "name": "교차 판매 / 업셀 전략",
        "phases": [
            "1단계 (0-1개월): 현재 사용 현황 분석 + 확장 기회 식별",
            "2단계 (1-3개월): 추가 제품 데모 + 비용 절감 시뮬레이션",
            "3단계 (3-6개월): 확장 계약 클로징 + 온보딩 지원",
        ],
        "key_tactics": ["사용량 분석", "잠재 니즈 발굴", "번들 할인 제안", "성공 사례 공유"],
        "success_metrics": ["ARPU 증가율", "제품 사용 수", "갱신 계약 금액", "고객 만족도"],
    },
    "new_market_penetration": {
        "name": "신규 시장 진입 전략",
        "phases": [
            "1단계 (0-2개월): 타겟 세그먼트 리서치 + 레퍼런스 고객 발굴",
            "2단계 (2-4개월): 산업별 특화 메시지 개발 + 파일럿 캠페인",
            "3단계 (4-6개월): 캠페인 확대 + 파트너 생태계 활성화",
        ],
        "key_tactics": ["산업별 가치 제안 차별화", "파트너 협업", "선도 고객 확보", "레퍼런스 구축"],
        "success_metrics": ["신규 파이프라인", "시장 점유율", "리드 전환율", "파트너 참여도"],
    },
}


class MarketingPlugin:
    """마케팅 전략 수립 및 캠페인 관리 플러그인"""

    @kernel_function(
        name="get_active_campaigns",
        description="현재 진행 중인 마케팅 캠페인 목록을 조회합니다. 캠페인명, 타겟, 성과 지표를 반환합니다.",
    )
    def get_active_campaigns(self) -> str:
        """진행 중인 캠페인 목록을 반환합니다"""
        active = [c for c in _CAMPAIGNS if c["status"] in ("Active", "Planning")]

        lines = [f"[진행 중인 캠페인 - {len(active)}개]"]
        for c in active:
            lines.append(
                f"\n[{c['id']}] {c['name']}\n"
                f"  유형: {c['type']} | 상태: {c['status']}\n"
                f"  기간: {c['start_date']} ~ {c['end_date']}\n"
                f"  타겟: {c['target_tier']} / {', '.join(c['target_industry'])}\n"
                f"  채널: {', '.join(c['channels'])}\n"
                f"  예산: {c['budget']:,}원 | 파이프라인: {c['pipeline_value']:,}원\n"
                f"  리드: {c['leads_generated']}개 | 미팅: {c['meetings_booked']}개\n"
                f"  핵심 메시지: {c['key_message']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="generate_marketing_strategy",
        description="고객의 상황에 맞는 마케팅 전략을 생성합니다. strategy_type을 입력하세요: 'enterprise_ai_adoption'(신규 대기업 AI 도입), 'at_risk_retention'(이탈 위험 고객 유지), 'cross_sell_upsell'(기존 고객 확대), 'new_market_penetration'(신규 시장 진입)",
    )
    def generate_marketing_strategy(
        self,
        strategy_type: str,
        company_name: str = "",
        specific_context: str = "",
    ) -> str:
        """마케팅 전략 템플릿을 기반으로 맞춤형 전략을 생성합니다"""
        template = _STRATEGY_TEMPLATES.get(strategy_type)
        if not template:
            types = list(_STRATEGY_TEMPLATES.keys())
            return f"'{strategy_type}' 전략 유형이 없습니다. 유효한 유형: {', '.join(types)}"

        company_str = f" (대상: {company_name})" if company_name else ""
        context_str = f"\n  맥락: {specific_context}" if specific_context else ""

        lines = [
            f"[{template['name']}{company_str}]{context_str}\n",
            "## 실행 단계",
        ]
        for phase in template["phases"]:
            lines.append(f"  {phase}")

        lines.append("\n## 핵심 전술")
        for tactic in template["key_tactics"]:
            lines.append(f"  - {tactic}")

        lines.append("\n## 성과 측정 지표")
        for metric in template["success_metrics"]:
            lines.append(f"  - {metric}")

        return "\n".join(lines)

    @kernel_function(
        name="calculate_campaign_roi",
        description="캠페인 ROI를 계산합니다. 캠페인 ID(예: CAM001)를 입력하면 투자 대비 성과를 분석합니다.",
    )
    def calculate_campaign_roi(self, campaign_id: str) -> str:
        """캠페인 ROI를 계산하고 반환합니다"""
        campaign = next((c for c in _CAMPAIGNS if c["id"].upper() == campaign_id.upper()), None)
        if not campaign:
            ids = [c["id"] for c in _CAMPAIGNS]
            return f"캠페인 ID '{campaign_id}'를 찾을 수 없습니다. 유효한 ID: {', '.join(ids)}"

        budget = campaign["budget"]
        pipeline = campaign["pipeline_value"]
        leads = campaign["leads_generated"]
        meetings = campaign["meetings_booked"]

        if budget == 0:
            return f"[{campaign['name']}] 예산 정보가 없어 ROI 계산이 불가합니다."

        pipeline_roi = ((pipeline - budget) / budget * 100) if pipeline > 0 else 0
        cost_per_lead = budget / leads if leads > 0 else 0
        cost_per_meeting = budget / meetings if meetings > 0 else 0
        lead_to_meeting = (meetings / leads * 100) if leads > 0 else 0

        return (
            f"[캠페인 ROI 분석: {campaign['name']}]\n"
            f"- 예산: {budget:,}원\n"
            f"- 창출 파이프라인: {pipeline:,}원\n"
            f"- 파이프라인 ROI: {pipeline_roi:.0f}%\n"
            f"- 리드 수: {leads}개 | 리드당 비용: {cost_per_lead:,.0f}원\n"
            f"- 미팅 수: {meetings}개 | 미팅당 비용: {cost_per_meeting:,.0f}원\n"
            f"- 리드→미팅 전환율: {lead_to_meeting:.1f}%\n"
            f"- 상태: {campaign['status']} ({campaign['start_date']} ~ {campaign['end_date']})"
        )

    @kernel_function(
        name="get_recommended_strategy_for_account",
        description="고객 상태와 딜 단계를 입력하면 최적 마케팅 전략 유형을 추천합니다. account_status: 'Active' 또는 'At-Risk', deal_stage: 'Discovery', 'PoC', 'Negotiation', 'Expansion'",
    )
    def get_recommended_strategy_for_account(
        self,
        account_status: str,
        deal_stage: str,
        tier: str = "Enterprise",
    ) -> str:
        """고객 상황에 맞는 마케팅 전략을 추천합니다"""
        status_lower = account_status.lower()
        stage_lower = deal_stage.lower()

        # 전략 추천 로직
        if status_lower == "at-risk":
            strategy_type = "at_risk_retention"
            reason = "이탈 위험 고객으로 신속한 리텐션 전략이 필요합니다."
        elif stage_lower == "expansion":
            strategy_type = "cross_sell_upsell"
            reason = "기존 성공 고객으로 추가 제품 확대 기회가 있습니다."
        elif stage_lower in ("discovery", "poc"):
            if tier.lower() == "enterprise":
                strategy_type = "enterprise_ai_adoption"
                reason = "대기업 신규 AI 도입 단계로 기술 검증과 임원 스폰서십이 핵심입니다."
            else:
                strategy_type = "new_market_penetration"
                reason = "중소기업 신규 고객으로 디지털 접점과 파일럿 지원이 효과적입니다."
        else:
            strategy_type = "enterprise_ai_adoption"
            reason = "협상/클로징 단계에서 가치 증명과 임원 레벨 지원이 필요합니다."

        template = _STRATEGY_TEMPLATES[strategy_type]
        return (
            f"[추천 전략: {template['name']}]\n"
            f"추천 이유: {reason}\n"
            f"전략 유형 코드: {strategy_type}\n\n"
            f"즉시 실행 전술:\n"
            + "\n".join(f"  - {t}" for t in template["key_tactics"][:3])
            + f"\n\n상세 전략 조회: generate_marketing_strategy('{strategy_type}') 함수를 활용하세요."
        )

    @kernel_function(
        name="get_marketing_summary",
        description="전체 마케팅 현황을 요약합니다. 총 캠페인 수, 예산, 파이프라인, 리드 수 등 핵심 지표를 반환합니다.",
    )
    def get_marketing_summary(self) -> str:
        """마케팅 현황 요약을 반환합니다"""
        total = len(_CAMPAIGNS)
        active = sum(1 for c in _CAMPAIGNS if c["status"] == "Active")
        total_budget = sum(c["budget"] for c in _CAMPAIGNS)
        total_pipeline = sum(c["pipeline_value"] for c in _CAMPAIGNS)
        total_leads = sum(c["leads_generated"] for c in _CAMPAIGNS)
        total_meetings = sum(c["meetings_booked"] for c in _CAMPAIGNS)
        overall_roi = ((total_pipeline - total_budget) / total_budget * 100) if total_budget > 0 else 0

        return (
            f"[마케팅 현황 요약]\n"
            f"- 총 캠페인: {total}개 (활성: {active}개)\n"
            f"- 총 예산: {total_budget:,}원\n"
            f"- 창출 파이프라인: {total_pipeline:,}원\n"
            f"- 전체 ROI: {overall_roi:.0f}%\n"
            f"- 총 리드: {total_leads}개 | 총 미팅: {total_meetings}개\n"
            f"- 리드→미팅 전환율: {(total_meetings/total_leads*100):.1f}%" if total_leads > 0 else ""
        )
