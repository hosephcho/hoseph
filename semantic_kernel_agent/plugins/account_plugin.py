"""
고객 정보(Account) 플러그인

CRM 데이터에서 고객 정보를 조회하고 관리하는 기능을 제공합니다.
실제 운영 환경에서는 Azure Cosmos DB, SQL Database 등에 연결합니다.
"""

from semantic_kernel.functions import kernel_function


# ── 샘플 데이터 (실제 환경에서는 DB 연결로 교체) ────────────────────────────
_ACCOUNTS: dict[str, dict] = {
    "ACC001": {
        "id": "ACC001",
        "company": "삼성전자",
        "industry": "전자/반도체",
        "tier": "Enterprise",
        "contact": "김철수 (kim.cs@samsung.com)",
        "annual_revenue": "300조원",
        "employees": 270000,
        "region": "서울/수원",
        "status": "Active",
        "since": "2018-03-15",
        "health_score": 92,
        "notes": "주요 클라우드 전환 프로젝트 진행 중. AI/ML 인프라 확장 관심",
    },
    "ACC002": {
        "id": "ACC002",
        "company": "LG화학",
        "industry": "화학/배터리",
        "tier": "Enterprise",
        "contact": "이영희 (lee.yh@lgchem.com)",
        "annual_revenue": "42조원",
        "employees": 22000,
        "region": "서울/대전",
        "status": "Active",
        "since": "2020-07-01",
        "health_score": 78,
        "notes": "배터리 생산 공정 최적화를 위한 AI 솔루션 검토 중",
    },
    "ACC003": {
        "id": "ACC003",
        "company": "카카오",
        "industry": "IT/플랫폼",
        "tier": "Mid-Market",
        "contact": "박지민 (jimin.park@kakao.com)",
        "annual_revenue": "8조원",
        "employees": 6500,
        "region": "판교",
        "status": "Active",
        "since": "2021-11-20",
        "health_score": 85,
        "notes": "추천 시스템 고도화 및 GPT 기반 챗봇 개발 프로젝트",
    },
    "ACC004": {
        "id": "ACC004",
        "company": "현대자동차",
        "industry": "자동차/모빌리티",
        "tier": "Enterprise",
        "contact": "최민준 (minjun.choi@hyundai.com)",
        "annual_revenue": "162조원",
        "employees": 120000,
        "region": "서울/울산",
        "status": "At-Risk",
        "since": "2019-05-10",
        "health_score": 61,
        "notes": "자율주행 AI 데이터 파이프라인 구축. 최근 경쟁사와 협의 중",
    },
    "ACC005": {
        "id": "ACC005",
        "company": "신한금융그룹",
        "industry": "금융/은행",
        "tier": "Enterprise",
        "contact": "정수진 (sujin.jung@shinhan.com)",
        "annual_revenue": "15조원",
        "employees": 22000,
        "region": "서울",
        "status": "Active",
        "since": "2022-01-15",
        "health_score": 88,
        "notes": "이상거래 탐지(FDS) AI 모델 고도화, 컴플라이언스 자동화",
    },
}


class AccountPlugin:
    """고객 정보 조회 및 관리 플러그인"""

    @kernel_function(
        name="get_account_by_id",
        description="고객 ID로 특정 고객의 상세 정보를 조회합니다. 계정 ID(예: ACC001)를 입력하면 회사명, 연락처, 매출, 계약 현황 등 상세 정보를 반환합니다.",
    )
    def get_account_by_id(self, account_id: str) -> str:
        """특정 고객의 상세 정보를 반환합니다"""
        acc = _ACCOUNTS.get(account_id.upper())
        if not acc:
            return f"고객 ID '{account_id}'을 찾을 수 없습니다. 유효한 ID: {', '.join(_ACCOUNTS.keys())}"

        return (
            f"[고객 정보]\n"
            f"- ID: {acc['id']}\n"
            f"- 회사명: {acc['company']}\n"
            f"- 산업군: {acc['industry']}\n"
            f"- 등급: {acc['tier']}\n"
            f"- 담당자: {acc['contact']}\n"
            f"- 연매출: {acc['annual_revenue']}\n"
            f"- 직원수: {acc['employees']:,}명\n"
            f"- 지역: {acc['region']}\n"
            f"- 상태: {acc['status']}\n"
            f"- 고객사 Since: {acc['since']}\n"
            f"- 건강 점수: {acc['health_score']}/100\n"
            f"- 메모: {acc['notes']}"
        )

    @kernel_function(
        name="search_accounts",
        description="회사명, 산업군, 지역, 상태(Active/At-Risk) 등 키워드로 고객 목록을 검색합니다. 예: '금융', '서울', 'Enterprise', 'At-Risk'",
    )
    def search_accounts(self, keyword: str) -> str:
        """키워드로 고객을 검색합니다"""
        keyword_lower = keyword.lower()
        matches = [
            acc for acc in _ACCOUNTS.values()
            if keyword_lower in acc["company"].lower()
            or keyword_lower in acc["industry"].lower()
            or keyword_lower in acc["region"].lower()
            or keyword_lower in acc["status"].lower()
            or keyword_lower in acc["tier"].lower()
            or keyword_lower in acc["notes"].lower()
        ]

        if not matches:
            return f"'{keyword}' 검색 결과가 없습니다."

        lines = [f"'{keyword}' 검색 결과 ({len(matches)}건):"]
        for acc in matches:
            lines.append(
                f"  [{acc['id']}] {acc['company']} | {acc['tier']} | "
                f"상태: {acc['status']} | 건강점수: {acc['health_score']}/100"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_at_risk_accounts",
        description="이탈 위험(At-Risk) 고객 목록을 조회합니다. 건강 점수가 낮거나 상태가 At-Risk인 고객을 반환합니다.",
    )
    def get_at_risk_accounts(self) -> str:
        """이탈 위험 고객 목록을 반환합니다"""
        at_risk = [
            acc for acc in _ACCOUNTS.values()
            if acc["status"] == "At-Risk" or acc["health_score"] < 70
        ]

        if not at_risk:
            return "현재 이탈 위험 고객이 없습니다."

        lines = [f"이탈 위험 고객 ({len(at_risk)}건):"]
        for acc in sorted(at_risk, key=lambda x: x["health_score"]):
            lines.append(
                f"  [{acc['id']}] {acc['company']} | 건강점수: {acc['health_score']}/100\n"
                f"    담당자: {acc['contact']}\n"
                f"    메모: {acc['notes']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_account_summary",
        description="전체 고객 현황을 요약합니다. 총 고객 수, 등급별/상태별 분포, 평균 건강점수를 반환합니다.",
    )
    def get_account_summary(self) -> str:
        """전체 고객 현황 요약을 반환합니다"""
        total = len(_ACCOUNTS)
        active = sum(1 for a in _ACCOUNTS.values() if a["status"] == "Active")
        at_risk = sum(1 for a in _ACCOUNTS.values() if a["status"] == "At-Risk")
        enterprise = sum(1 for a in _ACCOUNTS.values() if a["tier"] == "Enterprise")
        mid_market = sum(1 for a in _ACCOUNTS.values() if a["tier"] == "Mid-Market")
        avg_health = sum(a["health_score"] for a in _ACCOUNTS.values()) / total

        return (
            f"[고객 현황 요약]\n"
            f"- 총 고객 수: {total}개사\n"
            f"- 상태별: Active {active}개사, At-Risk {at_risk}개사\n"
            f"- 등급별: Enterprise {enterprise}개사, Mid-Market {mid_market}개사\n"
            f"- 평균 건강 점수: {avg_health:.1f}/100\n"
            f"- 주요 산업군: 전자/반도체, 화학/배터리, IT/플랫폼, 자동차, 금융"
        )
