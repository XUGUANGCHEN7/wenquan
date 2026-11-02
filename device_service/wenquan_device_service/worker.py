from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class WorkerBackendError(RuntimeError):
    pass


class DeviceFailure(RuntimeError):
    """A known SDK/reader rejection where no state was changed."""


class DeviceUncertain(RuntimeError):
    """The command may have reached hardware; do not retry automatically."""


class WorkerBackend(Protocol):
    def poll(self) -> dict | None: ...
    def claim(self, task: dict) -> None: ...
    def start(self, task: dict) -> None: ...
    def report(self, task: dict, result: str, raw_error: str = "") -> None: ...


class DeviceAdapter(Protocol):
    def execute(self, task: dict) -> None: ...


class MockAdapter:
    def __init__(self, result: str = "SUCCEEDED"):
        self.result = result.upper()

    def execute(self, task: dict) -> None:
        if self.result == "FAILED":
            raise DeviceFailure("mock adapter reported a known failure")
        if self.result == "UNKNOWN":
            raise DeviceUncertain("mock uncertain result")
        return None


class TaskWorker:
    def __init__(self, backend: WorkerBackend, adapter: DeviceAdapter, *, worker_id: str,
                 reader_id: str, journal_path: Path | str | None = None):
        self.backend = backend
        self.adapter = adapter
        self.worker_id = worker_id
        self.reader_id = reader_id
        self.journal_path = Path(journal_path) if journal_path else None

    def _retry_journal(self) -> None:
        if not self.journal_path or not self.journal_path.exists():
            return
        record = json.loads(self.journal_path.read_text(encoding="utf-8"))
        self.backend.report(record["task"], record["result"], record.get("raw_error", ""))
        self.journal_path.unlink()

    def _persist(self, task: dict, result: str, raw_error: str) -> None:
        if not self.journal_path:
            return
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.journal_path.write_text(json.dumps({
            "task": task, "result": result, "raw_error": raw_error,
        }, ensure_ascii=False), encoding="utf-8")

    def _report(self, task: dict, result: str, raw_error: str = "") -> None:
        try:
            self.backend.report(task, result, raw_error)
        except WorkerBackendError:
            self._persist(task, result, raw_error)
            raise

    def process_once(self) -> bool:
        self._retry_journal()
        task = self.backend.poll()
        if task is None:
            return False
        self.backend.claim(task)
        self.backend.start(task)
        try:
            self.adapter.execute(task)
        except DeviceFailure as exc:
            self._report(task, "FAILED", str(exc))
        except DeviceUncertain as exc:
            self._report(task, "UNKNOWN", str(exc))
        except Exception as exc:
            self._report(task, "UNKNOWN", f"unexpected adapter outcome: {exc}")
        else:
            self._report(task, "SUCCEEDED")
        return True
