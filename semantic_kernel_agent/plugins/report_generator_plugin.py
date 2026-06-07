"""
보고서 생성 플러그인

석유화학 BI 보고서를 마크다운·JSON 형식으로 파일에 저장하고
선택적으로 Azure Blob Storage에 업로드합니다.

출력 파일 구조:
  output/reports/
  ├── YYYY-MM-DD_daily_ko.md   ← 한국어 일간 보고서
  ├── YYYY-MM-DD_daily_en.md   ← 영어 일간 보고서
  ├── YYYY-MM-DD_daily.json    ← 기계 가독형 JSON 요약
  └── YYYY-MM-DD_weekly_ko.md  ← 주간 보고서 (weekly 타입)
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from semantic_kernel.functions import kernel_function

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "reports",
)
REPORTS_DIR = os.environ.get("PETROCHEM_OUTPUT_DIR", _DEFAULT_OUTPUT_DIR)

# Azure Blob Storage (선택)
_AZURE_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")


class ReportGeneratorPlugin:
    """
    BI 보고서 파일 저장 및 관리 플러그인.
    LLM 호출 없이 순수 I/O와 포맷팅만 수행합니다.
    """

    def _ensure_output_dir(self) -> None:
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def _get_filename(self, report_type: str, lang: str, date_str: str | None = None) -> str:
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ext = "md" if lang != "json" else "json"
        suffix = "" if lang == "json" else f"_{lang}"
        return os.path.join(REPORTS_DIR, f"{date_str}_{report_type}{suffix}.{ext}")

    @kernel_function(
        name="save_markdown_report",
        description=(
            "한국어·영어 BI 보고서를 마크다운 파일로 저장합니다. "
            "ReportAgent가 생성한 보고서 텍스트를 파일로 영구 저장할 때 사용합니다. "
            "저장된 파일 경로를 반환합니다."
        ),
    )
    def save_markdown_report(
        self,
        content_ko: Annotated[str, "한국어 보고서 본문 (마크다운 형식)"],
        content_en: Annotated[str, "영어 보고서 본문 (마크다운 형식)"],
        report_type: Annotated[str, "보고서 유형: daily 또는 weekly (기본값: daily)"] = "daily",
        title: Annotated[str, "보고서 제목 (기본값: 자동 생성)"] = "",
    ) -> str:
        """한국어·영어 보고서 마크다운 파일을 저장합니다."""
        self._ensure_output_dir()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if not title:
            type_label = "일간" if report_type == "daily" else "주간"
            title = f"석유화학 시장 {type_label} BI 보고서 ({today})"

        ko_path = self._get_filename(report_type, "ko", today)
        en_path = self._get_filename(report_type, "en", today)

        ko_content = f"# {title}\n\n{content_ko}"
        en_title = title.replace("일간", "Daily").replace("주간", "Weekly").replace("석유화학 시장", "Petrochemical Market").replace("BI 보고서", "BI Report")
        en_content = f"# {en_title}\n\n{content_en}"

        with open(ko_path, "w", encoding="utf-8") as f:
            f.write(ko_content)
        with open(en_path, "w", encoding="utf-8") as f:
            f.write(en_content)

        return json.dumps({
            "status": "saved",
            "date": today,
            "report_type": report_type,
            "files": {"korean": ko_path, "english": en_path},
        }, ensure_ascii=False)

    @kernel_function(
        name="save_json_summary",
        description=(
            "보고서 데이터를 기계 가독형 JSON 파일로 저장합니다. "
            "향후 Power BI, 데이터베이스 연동, 자동화 파이프라인에 활용됩니다."
        ),
    )
    def save_json_summary(
        self,
        summary_data_json: Annotated[str, "저장할 요약 데이터 (JSON 문자열)"],
        report_type: Annotated[str, "보고서 유형: daily 또는 weekly"] = "daily",
    ) -> str:
        """JSON 요약 파일을 저장합니다."""
        self._ensure_output_dir()
        try:
            data = json.loads(summary_data_json)
        except json.JSONDecodeError:
            data = {"raw": summary_data_json}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data["report_type"] = report_type

        json_path = self._get_filename(report_type, "json", today)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return json.dumps({"status": "saved", "path": json_path}, ensure_ascii=False)

    @kernel_function(
        name="load_previous_report",
        description=(
            "이전 보고서를 불러옵니다. "
            "이전 보고서와 비교하여 변화 사항을 하이라이트할 때 사용합니다."
        ),
    )
    def load_previous_report(
        self,
        report_type: Annotated[str, "보고서 유형: daily 또는 weekly"] = "daily",
        days_ago: Annotated[int, "며칠 전 보고서를 불러올지 (기본값: 1)"] = 1,
        language: Annotated[str, "ko 또는 en (기본값: ko)"] = "ko",
    ) -> str:
        """이전 날짜의 보고서 파일을 로드합니다."""
        target_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        path = self._get_filename(report_type, language, target_date)

        if not os.path.exists(path):
            return f"{target_date} {report_type} 보고서 파일이 없습니다: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"# 이전 보고서 ({target_date})\n\n{content}"
        except OSError as e:
            return f"파일 읽기 오류: {str(e)}"

    @kernel_function(
        name="list_saved_reports",
        description="저장된 보고서 파일 목록을 반환합니다.",
    )
    def list_saved_reports(
        self,
        report_type: Annotated[str, "daily, weekly, 또는 all (기본값: all)"] = "all",
    ) -> str:
        """저장된 보고서 목록을 반환합니다."""
        if not os.path.exists(REPORTS_DIR):
            return "보고서 디렉토리가 없습니다."

        files = sorted(os.listdir(REPORTS_DIR), reverse=True)
        if report_type != "all":
            files = [f for f in files if report_type in f]

        if not files:
            return "저장된 보고서가 없습니다."

        lines = [f"저장된 보고서 ({REPORTS_DIR}):"]
        for fname in files[:20]:  # 최대 20개
            fpath = os.path.join(REPORTS_DIR, fname)
            size = os.path.getsize(fpath)
            lines.append(f"  - {fname} ({size:,} bytes)")
        return "\n".join(lines)

    @kernel_function(
        name="upload_to_azure_blob",
        description=(
            "보고서 파일을 Azure Blob Storage에 업로드합니다. "
            "AZURE_STORAGE_CONNECTION_STRING 환경변수가 설정된 경우에만 동작합니다."
        ),
    )
    def upload_to_azure_blob(
        self,
        file_path: Annotated[str, "업로드할 로컬 파일 경로"],
        container_name: Annotated[str, "Azure Blob 컨테이너 이름 (기본값: petrochem-reports)"] = "petrochem-reports",
    ) -> str:
        """Azure Blob Storage에 파일을 업로드합니다."""
        if not _AZURE_CONN_STR:
            return "AZURE_STORAGE_CONNECTION_STRING이 설정되지 않아 업로드를 건너뜁니다."

        if not os.path.exists(file_path):
            return f"파일을 찾을 수 없습니다: {file_path}"

        try:
            from azure.storage.blob import BlobServiceClient
            blob_name = os.path.basename(file_path)
            client = BlobServiceClient.from_connection_string(_AZURE_CONN_STR)
            container = client.get_container_client(container_name)

            # 컨테이너 없으면 생성
            if not container.exists():
                container.create_container()

            with open(file_path, "rb") as data:
                container.upload_blob(name=blob_name, data=data, overwrite=True)

            return json.dumps({
                "status": "uploaded",
                "container": container_name,
                "blob": blob_name,
            }, ensure_ascii=False)
        except ImportError:
            return "azure-storage-blob 패키지가 설치되지 않았습니다. pip install azure-storage-blob"
        except Exception as e:
            return f"업로드 실패: {str(e)}"
