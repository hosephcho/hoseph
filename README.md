# Azure ML + Semantic Kernel Agentic AI

Azure ML 환경에서 Semantic Kernel을 활용한 Agentic AI 구현 가이드 및 샘플 코드입니다.

---

## 목차

1. [Azure ML 환경 설정](#1-azure-ml-환경-설정)
2. [Semantic Kernel vs LangChain in Azure ML](#2-semantic-kernel-vs-langchain-in-azure-ml)
3. [패키지 설치](#3-패키지-설치)
4. [인증 설정](#4-인증-설정)
5. [환경 변수 설정](#5-환경-변수-설정)
6. [샘플 코드 구성](#6-샘플-코드-구성)
7. [실행 방법](#7-실행-방법)

---

## 1. Azure ML 환경 설정

### Azure ML에서 Semantic Kernel 사용 시 필요한 설정

#### 1.1 Compute Instance / Compute Cluster 요구사항

| 항목 | 권장 사양 |
|------|-----------|
| Python 버전 | 3.9 이상 (3.10, 3.11 권장) |
| CUDA | 불필요 (API 호출 기반) |
| 메모리 | 최소 8GB RAM |
| 네트워크 | Azure OpenAI 엔드포인트 접근 가능 |

#### 1.2 Azure ML Workspace 설정

**필수 설정 항목:**

1. **Managed Identity 활성화** (권장)
   - Azure ML Compute Instance에 System-assigned Managed Identity 활성화
   - Azure OpenAI 리소스에 `Cognitive Services OpenAI User` 역할 부여

2. **Network 설정**
   - Private endpoint 사용 시: Azure OpenAI도 동일한 VNet에 배치 필요
   - Public endpoint 사용 시: Outbound 443 포트 허용 확인

3. **Key Vault 연동** (선택)
   - API Key를 Azure Key Vault에 저장하고 ML에서 참조하는 방식 권장

#### 1.3 Azure OpenAI 리소스 설정

```
Azure Portal > Azure OpenAI > 배포 설정:
- 모델 배포 이름 (예: gpt-4o, gpt-4-turbo)
- API 버전: 2024-02-01 이상 권장
- 엔드포인트 URL 확인
```

#### 1.4 특별히 추가 설정이 필요한 항목 (Azure ML 전용)

```bash
# Azure ML Compute Instance 내부에서 실행
# 프록시 설정 확인 (기업 환경의 경우)
echo $HTTPS_PROXY
echo $HTTP_PROXY

# Azure ML 기본 환경에는 일부 패키지가 없으므로 반드시 설치 필요
pip install semantic-kernel azure-identity

# Azure ML의 경우 환경 격리를 위해 conda 환경 사용 권장
conda create -n sk-agent python=3.11
conda activate sk-agent
pip install -r requirements.txt
```

---

## 2. Semantic Kernel vs LangChain in Azure ML

| 비교 항목 | Semantic Kernel | LangChain |
|-----------|----------------|-----------|
| Microsoft 공식 지원 | **Yes** (MS 개발) | No |
| Azure OpenAI 통합 | 네이티브 지원 | 추가 설정 필요 |
| Azure Identity 통합 | 네이티브 지원 | 부분 지원 |
| Azure ML SDK 호환성 | 높음 | 보통 |
| 의존성 충돌 위험 | 낮음 | 높음 (많은 의존성) |
| Planner/Agent 기능 | 내장 (Auto Function Calling) | 다양한 Agent 타입 |
| 한국어 문서 | 부족 | 풍부 |

> **결론**: Azure ML 환경에서는 Microsoft가 직접 개발한 Semantic Kernel이 Azure 서비스와의 호환성 및 인증 통합 면에서 더 안정적입니다.

---

## 3. 패키지 설치

```bash
pip install -r requirements.txt
```

`requirements.txt` 주요 패키지:
- `semantic-kernel>=1.0.0`: 핵심 프레임워크
- `azure-identity`: Managed Identity / Azure AD 인증
- `azure-keyvault-secrets`: Key Vault에서 시크릿 로드 (선택)
- `openai>=1.0.0`: Azure OpenAI 클라이언트 (SK 내부에서 사용)

---

## 4. 인증 설정

### 방법 1: Managed Identity (Azure ML 내부 - 권장)

```python
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

# Azure ML Compute Instance에서는 자동으로 Managed Identity 사용
credential = DefaultAzureCredential()
```

### 방법 2: API Key 직접 사용 (개발/테스트용)

```python
import os
os.environ["AZURE_OPENAI_API_KEY"] = "your-api-key"
```

### 방법 3: Azure Key Vault 연동

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

kv_client = SecretClient(
    vault_url="https://your-keyvault.vault.azure.net",
    credential=DefaultAzureCredential()
)
api_key = kv_client.get_secret("azure-openai-key").value
```

---

## 5. 환경 변수 설정

`.env` 파일 또는 Azure ML Environment Variables에 설정:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

Azure ML Studio에서 설정하는 방법:
```
Jobs > Environment variables 섹션에 추가
또는
Compute Instance > Environment 탭에서 추가
```

---

## 6. 샘플 코드 구성

```
semantic_kernel_agent/
├── 01_basic_chat.py              # 기본 채팅 완성
├── 02_function_calling.py        # Function Calling (Tool Use)
├── 03_auto_function_calling.py   # Auto Function Calling Agent
├── 04_multi_agent.py             # Multi-Agent 협업
├── plugins/
│   ├── math_plugin.py            # 수학 계산 플러그인
│   ├── web_search_plugin.py      # 웹 검색 플러그인 (시뮬레이션)
│   └── data_analysis_plugin.py   # 데이터 분석 플러그인
└── config/
    └── settings.py               # 공통 설정
```

---

## 7. 실행 방법

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에 Azure OpenAI 정보 입력

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 기본 채팅 테스트
python semantic_kernel_agent/01_basic_chat.py

# 4. Function Calling 테스트
python semantic_kernel_agent/02_function_calling.py

# 5. Auto Function Calling Agent (핵심 Agentic AI)
python semantic_kernel_agent/03_auto_function_calling.py

# 6. Multi-Agent 시나리오
python semantic_kernel_agent/04_multi_agent.py
```
