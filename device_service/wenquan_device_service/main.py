from __future__ import annotations

import os
import time
from pathlib import Path

from .client import HttpBackend
from .worker import MockAdapter, TaskWorker, WorkerBackendError


def main() -> None:
    api_base = os.environ.get("WENQUAN_API_BASE", "http://127.0.0.1:8000/api/v1")
    token = os.environ.get("WENQUAN_DEVICE_TOKEN", "dev-device-service-change-me")
    worker_id = os.environ.get("WENQUAN_WORKER_ID", "windows-frontdesk-01")
    reader_id = os.environ.get("WENQUAN_READER_ID", "mock-reader")
    mock_result = os.environ.get("WENQUAN_MOCK_RESULT", "SUCCEEDED")
    interval = float(os.environ.get("WENQUAN_POLL_SECONDS", "2"))
    journal = Path(os.environ.get("WENQUAN_RESULT_JOURNAL", "./pending-device-result.json"))

    backend = HttpBackend(api_base, token, worker_id=worker_id, reader_id=reader_id)
    worker = TaskWorker(backend, MockAdapter(mock_result), worker_id=worker_id,
                        reader_id=reader_id, journal_path=journal)
    delay = interval
    while True:
        try:
            worked = worker.process_once()
            delay = interval
        except WorkerBackendError as exc:
            # No local hardware retry is implied by a backend outage. Exponential backoff
            # only retries HTTP polling; hardware commands are never replayed automatically.
            print(f"device backend unavailable: {exc}", flush=True)
            delay = min(delay * 2, 60)
            worked = False
        if not worked:
            time.sleep(delay)


if __name__ == "__main__":
    main()
