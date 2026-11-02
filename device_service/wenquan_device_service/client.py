from __future__ import annotations

import httpx

from .worker import WorkerBackend, WorkerBackendError


class HttpBackend(WorkerBackend):
    def __init__(self, base_url: str, token: str, *, worker_id: str, reader_id: str,
                 timeout: float = 10.0):
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        self.worker_id = worker_id
        self.reader_id = reader_id

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | None:
        try:
            response = self.client.request(method, path, json=body)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WorkerBackendError(str(exc)) from exc

    def poll(self) -> dict | None:
        return self._request("POST", "/devices/tasks/poll", {
            "worker_id": self.worker_id, "reader_id": self.reader_id,
        })

    def claim(self, task: dict) -> None:
        self._request("POST", f"/devices/tasks/{task['id']}/claim", {
            "worker_id": self.worker_id, "reader_id": self.reader_id,
        })

    def start(self, task: dict) -> None:
        self._request("POST", f"/devices/tasks/{task['id']}/start", {"worker_id": self.worker_id})

    def report(self, task: dict, result: str, raw_error: str = "") -> None:
        self._request("POST", f"/devices/tasks/{task['id']}/result", {
            "worker_id": self.worker_id, "result": result, "raw_error": raw_error,
        })
