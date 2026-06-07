"""
Azure ML + Semantic Kernel 공통 설정 모듈

Azure ML 환경에서는 두 가지 인증 방식을 지원합니다:
1. Managed Identity (Azure ML Compute Instance - 권장)
2. API Key (.env 파일 - 로컬 개발용)
"""

import os
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 기본 베이스 경로
#   Windows 로컬 실행: C:\Users\hosep\OneDrive\문서\Claude
#   Linux / Azure ML:  프로젝트 루트 기준 상대 경로
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    _BASE_DIR = os.path.join(
        os.path.expanduser("~"), "OneDrive", "문서", "Claude"
    )
else:
    # 이 파일 기준 두 단계 위 = 프로젝트 루트
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Azure ML 환경에서는 환경변수가 이미 설정되어 있음


@dataclass
class AzureOpenAIConfig:
    endpoint: str
    deployment_name: str
    api_version: str
    api_key: str | None = None  # Managed Identity 사용 시 None


def get_azure_openai_config() -> AzureOpenAIConfig:
    """
    환경 변수에서 Azure OpenAI 설정을 로드합니다.

    Azure ML Compute Instance에서는 Managed Identity를 통해
    api_key 없이도 인증 가능합니다.
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")  # 없으면 Managed Identity 사용

    if not endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT 환경 변수가 설정되지 않았습니다.\n"
            "Azure ML에서는 Compute Instance의 Environment Variables에 설정하거나\n"
            ".env 파일을 사용하세요."
        )

    return AzureOpenAIConfig(
        endpoint=endpoint,
        deployment_name=deployment,
        api_version=api_version,
        api_key=api_key,
    )


def get_petrochem_config() -> dict:
    """
    석유화학 BI Agent 관련 설정을 로드합니다.

    기본 경로:
      Windows: C:\\Users\\hosep\\OneDrive\\문서\\Claude\\output\\reports
      Linux  : <프로젝트 루트>/output/reports

    환경변수(PETROCHEM_OUTPUT_DIR, PETROCHEM_PRICE_CACHE_DIR)로 덮어쓸 수 있습니다.
    """
    default_output_dir = os.path.join(_BASE_DIR, "output", "reports")
    default_cache_dir = os.path.join(_BASE_DIR, "data", "price_cache")

    return {
        "output_dir": os.environ.get("PETROCHEM_OUTPUT_DIR", default_output_dir),
        "price_cache_dir": os.environ.get("PETROCHEM_PRICE_CACHE_DIR", default_cache_dir),
        "spglobal_api_key": os.environ.get("SPGLOBAL_API_KEY", ""),
        "icis_api_key": os.environ.get("ICIS_API_KEY", ""),
        "azure_storage_conn_str": os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
        "base_dir": _BASE_DIR,
    }
