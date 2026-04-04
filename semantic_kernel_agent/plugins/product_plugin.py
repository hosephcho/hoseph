"""
제품 정보(Product) 플러그인

Azure 기반 AI/클라우드 제품 카탈로그를 조회하고 추천하는 기능을 제공합니다.
실제 환경에서는 제품 DB 또는 ERP 시스템과 연동합니다.
"""

from semantic_kernel.functions import kernel_function


# ── 샘플 제품 카탈로그 ────────────────────────────────────────────────────────
_PRODUCTS: dict[str, dict] = {
    "PROD001": {
        "id": "PROD001",
        "name": "Azure OpenAI Service",
        "category": "AI/ML",
        "subcategory": "생성형 AI",
        "description": "GPT-4, DALL-E 등 최신 OpenAI 모델을 Azure 환경에서 안전하게 사용",
        "pricing": "토큰 기반 종량제 (GPT-4o: $5/1M input tokens)",
        "target_industry": ["IT/플랫폼", "금융/은행", "전자/반도체", "자동차/모빌리티"],
        "use_cases": ["챗봇/가상 어시스턴트", "문서 분석", "코드 생성", "번역/요약"],
        "compliance": ["ISO 27001", "SOC 2", "GDPR", "금융감독원 가이드"],
        "availability": "GA",
        "annual_deal_size": "5천만 ~ 5억원",
    },
    "PROD002": {
        "id": "PROD002",
        "name": "Azure Machine Learning",
        "category": "AI/ML",
        "subcategory": "ML 플랫폼",
        "description": "엔터프라이즈급 ML 파이프라인 구축, 모델 학습/배포/모니터링 통합 플랫폼",
        "pricing": "컴퓨팅 사용량 기반 (Compute Cluster, Managed Endpoints)",
        "target_industry": ["전자/반도체", "화학/배터리", "자동차/모빌리티", "제조"],
        "use_cases": ["예측 모델", "이상 탐지", "공정 최적화", "수요 예측"],
        "compliance": ["ISO 27001", "SOC 2", "HIPAA"],
        "availability": "GA",
        "annual_deal_size": "1억 ~ 10억원",
    },
    "PROD003": {
        "id": "PROD003",
        "name": "Azure AI Search",
        "category": "AI/ML",
        "subcategory": "검색/RAG",
        "description": "벡터 검색과 하이브리드 검색을 결합한 엔터프라이즈 검색 솔루션. RAG 구현에 최적",
        "pricing": "인스턴스 크기 기반 월정액 + 인덱스 용량",
        "target_industry": ["금융/은행", "IT/플랫폼", "법무/컴플라이언스"],
        "use_cases": ["사내 지식 검색", "RAG 기반 챗봇", "문서 Q&A", "제품 검색"],
        "compliance": ["ISO 27001", "SOC 2", "GDPR"],
        "availability": "GA",
        "annual_deal_size": "3천만 ~ 3억원",
    },
    "PROD004": {
        "id": "PROD004",
        "name": "Azure Cosmos DB",
        "category": "데이터베이스",
        "subcategory": "NoSQL/벡터 DB",
        "description": "글로벌 분산 다중 모델 DB. 벡터 임베딩 저장 및 유사도 검색 지원",
        "pricing": "RU/s 기반 프로비저닝 또는 서버리스",
        "target_industry": ["IT/플랫폼", "게임", "IoT", "전자/반도체"],
        "use_cases": ["실시간 데이터 처리", "벡터 스토어", "세션 관리", "IoT 데이터"],
        "compliance": ["ISO 27001", "SOC 2", "GDPR", "PCI DSS"],
        "availability": "GA",
        "annual_deal_size": "5천만 ~ 5억원",
    },
    "PROD005": {
        "id": "PROD005",
        "name": "Azure Synapse Analytics",
        "category": "데이터 분석",
        "subcategory": "데이터 웨어하우스",
        "description": "데이터 통합, 빅데이터 분석, ML 워크로드를 통합하는 분석 플랫폼",
        "pricing": "DWU(데이터 웨어하우스 단위) 기반",
        "target_industry": ["금융/은행", "유통/리테일", "화학/배터리", "자동차/모빌리티"],
        "use_cases": ["실시간 분석", "배치 ETL", "비즈니스 인텔리전스", "예측 분석"],
        "compliance": ["ISO 27001", "SOC 2", "HIPAA", "금융보안원 인증"],
        "availability": "GA",
        "annual_deal_size": "2억 ~ 20억원",
    },
    "PROD006": {
        "id": "PROD006",
        "name": "Microsoft Copilot for Microsoft 365",
        "category": "생산성",
        "subcategory": "AI 어시스턴트",
        "description": "Word, Excel, Teams, Outlook에 통합된 AI 어시스턴트. 업무 생산성 혁신",
        "pricing": "사용자당 월 $30 (연간 계약)",
        "target_industry": ["전 산업군"],
        "use_cases": ["회의록 자동화", "문서 작성", "이메일 요약", "데이터 분석"],
        "compliance": ["ISO 27001", "SOC 2", "GDPR"],
        "availability": "GA",
        "annual_deal_size": "사용자 수 × $360/년",
    },
}


class ProductPlugin:
    """제품 정보 조회 및 추천 플러그인"""

    @kernel_function(
        name="get_product_by_id",
        description="제품 ID로 특정 제품의 상세 정보를 조회합니다. 제품 ID(예: PROD001)를 입력하면 제품명, 설명, 가격, 사용 사례 등을 반환합니다.",
    )
    def get_product_by_id(self, product_id: str) -> str:
        """제품 ID로 상세 정보를 반환합니다"""
        prod = _PRODUCTS.get(product_id.upper())
        if not prod:
            return f"제품 ID '{product_id}'를 찾을 수 없습니다. 유효한 ID: {', '.join(_PRODUCTS.keys())}"

        use_cases_str = ", ".join(prod["use_cases"])
        industries_str = ", ".join(prod["target_industry"])
        compliance_str = ", ".join(prod["compliance"])

        return (
            f"[제품 상세 정보]\n"
            f"- ID: {prod['id']}\n"
            f"- 제품명: {prod['name']}\n"
            f"- 카테고리: {prod['category']} > {prod['subcategory']}\n"
            f"- 설명: {prod['description']}\n"
            f"- 가격 정책: {prod['pricing']}\n"
            f"- 예상 연간 딜 규모: {prod['annual_deal_size']}\n"
            f"- 주요 사용 사례: {use_cases_str}\n"
            f"- 타겟 산업군: {industries_str}\n"
            f"- 컴플라이언스: {compliance_str}\n"
            f"- 출시 상태: {prod['availability']}"
        )

    @kernel_function(
        name="search_products",
        description="카테고리, 산업군, 사용 사례 키워드로 제품을 검색합니다. 예: 'AI', '금융', 'RAG', '챗봇', '분석', 'ML'",
    )
    def search_products(self, keyword: str) -> str:
        """키워드로 제품을 검색합니다"""
        keyword_lower = keyword.lower()
        matches = [
            prod for prod in _PRODUCTS.values()
            if keyword_lower in prod["name"].lower()
            or keyword_lower in prod["category"].lower()
            or keyword_lower in prod["subcategory"].lower()
            or keyword_lower in prod["description"].lower()
            or any(keyword_lower in uc.lower() for uc in prod["use_cases"])
            or any(keyword_lower in ind.lower() for ind in prod["target_industry"])
        ]

        if not matches:
            return f"'{keyword}' 키워드와 매칭되는 제품이 없습니다."

        lines = [f"'{keyword}' 검색 결과 ({len(matches)}개 제품):"]
        for prod in matches:
            lines.append(
                f"  [{prod['id']}] {prod['name']}\n"
                f"    카테고리: {prod['category']} | 딜 규모: {prod['annual_deal_size']}\n"
                f"    설명: {prod['description'][:60]}..."
            )
        return "\n".join(lines)

    @kernel_function(
        name="recommend_products_for_account",
        description="고객의 산업군과 니즈에 맞는 제품을 추천합니다. 산업군(예: '금융/은행', '전자/반도체')과 니즈(예: 'AI 챗봇', '데이터 분석')를 입력하세요.",
    )
    def recommend_products_for_account(self, industry: str, needs: str) -> str:
        """고객 산업군과 니즈에 맞는 제품을 추천합니다"""
        industry_lower = industry.lower()
        needs_lower = needs.lower()

        scored: list[tuple[int, dict]] = []
        for prod in _PRODUCTS.values():
            score = 0
            # 산업군 매칭
            for ind in prod["target_industry"]:
                if industry_lower in ind.lower() or ind == "전 산업군":
                    score += 3
                    break
            # 니즈/사용사례 매칭
            for uc in prod["use_cases"]:
                if any(word in uc.lower() for word in needs_lower.split()):
                    score += 2
            # 설명 매칭
            if any(word in prod["description"].lower() for word in needs_lower.split()):
                score += 1
            if score > 0:
                scored.append((score, prod))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return f"'{industry}' 산업군의 '{needs}' 니즈에 맞는 제품 추천 결과가 없습니다."

        lines = [f"[추천 제품 - {industry} / {needs}]"]
        for rank, (score, prod) in enumerate(scored[:3], 1):
            lines.append(
                f"\n{rank}위: {prod['name']} (적합도: {score}점)\n"
                f"   설명: {prod['description']}\n"
                f"   주요 사용 사례: {', '.join(prod['use_cases'][:3])}\n"
                f"   가격: {prod['pricing']}\n"
                f"   딜 규모: {prod['annual_deal_size']}"
            )
        return "\n".join(lines)

    @kernel_function(
        name="get_product_catalog",
        description="전체 제품 카탈로그 목록을 반환합니다. 어떤 제품이 있는지 확인할 때 사용합니다.",
    )
    def get_product_catalog(self) -> str:
        """전체 제품 카탈로그를 반환합니다"""
        lines = [f"[전체 제품 카탈로그 - {len(_PRODUCTS)}개 제품]\n"]
        for prod in _PRODUCTS.values():
            lines.append(
                f"[{prod['id']}] {prod['name']}\n"
                f"  카테고리: {prod['category']} > {prod['subcategory']}\n"
                f"  딜 규모: {prod['annual_deal_size']}\n"
            )
        return "\n".join(lines)
