"""
Query History 모듈

사용자가 입력한 query를 최대 10개까지 세션 내에서 유지합니다.
- collections.deque(maxlen=10)을 사용하여 가장 오래된 항목을 자동 제거
- 각 항목: {"id": int, "timestamp": str, "query": str}
- 선택적으로 JSON 파일에 영속화(persist) 가능

사용 예:
    history = QueryHistory()
    history.add("Azure ML이란?")
    history.add("Semantic Kernel 사용법 알려줘")
    history.display()
    recent = history.get_recent(3)
"""

import json
import os
from collections import deque
from datetime import datetime


class QueryHistory:
    """
    사용자 query를 최대 MAX_SIZE개까지 저장하는 히스토리 클래스.

    세션이 종료되어도 persist_path가 지정된 경우 JSON 파일에 저장됩니다.
    """

    MAX_SIZE = 10

    def __init__(self, persist_path: str | None = None):
        """
        Args:
            persist_path: JSON 파일 경로. 지정 시 자동으로 로드/저장.
                          None이면 세션 메모리만 사용.
        """
        self._history: deque[dict] = deque(maxlen=self.MAX_SIZE)
        self._counter: int = 0
        self.persist_path = persist_path

        if persist_path:
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, query: str) -> None:
        """새 query를 히스토리에 추가합니다. MAX_SIZE 초과 시 가장 오래된 항목 자동 제거."""
        self._counter += 1
        entry = {
            "id": self._counter,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query.strip(),
        }
        self._history.append(entry)

        if self.persist_path:
            self._save()

    def get_all(self) -> list[dict]:
        """저장된 모든 query를 최신 순(오래된 것 → 최신 것)으로 반환합니다."""
        return list(self._history)

    def get_recent(self, n: int = 3) -> list[dict]:
        """최근 n개의 query를 반환합니다 (n > MAX_SIZE이면 MAX_SIZE로 제한)."""
        n = min(n, self.MAX_SIZE)
        items = list(self._history)
        return items[-n:] if len(items) >= n else items

    def get_queries_only(self) -> list[str]:
        """query 문자열만 추출하여 리스트로 반환합니다."""
        return [entry["query"] for entry in self._history]

    def clear(self) -> None:
        """히스토리를 초기화합니다."""
        self._history.clear()
        if self.persist_path and os.path.exists(self.persist_path):
            os.remove(self.persist_path)

    def __len__(self) -> int:
        return len(self._history)

    def display(self) -> None:
        """히스토리를 보기 좋게 출력합니다."""
        if not self._history:
            print("[Query History] 기록이 없습니다.")
            return

        print(f"\n{'=' * 60}")
        print(f"  Query History (최근 {len(self._history)}개 / 최대 {self.MAX_SIZE}개)")
        print(f"{'=' * 60}")
        for entry in self._history:
            print(f"  [{entry['id']:>3}] {entry['timestamp']}  {entry['query']}")
        print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # 영속화 (선택)
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """현재 히스토리를 JSON 파일에 저장합니다."""
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            data = {
                "counter": self._counter,
                "history": list(self._history),
            }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 파일 저장 실패는 무시 (메모리는 유지)

    def _load(self) -> None:
        """JSON 파일에서 이전 히스토리를 로드합니다."""
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._counter = data.get("counter", 0)
            # maxlen을 유지하면서 로드 (MAX_SIZE 초과분은 자동 제거)
            for entry in data.get("history", []):
                self._history.append(entry)
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # 손상된 파일은 무시하고 빈 히스토리로 시작
