import json

import pytest

from wenquan_device_service.worker import (
    DeviceFailure, DeviceUncertain, MockAdapter, TaskWorker, WorkerBackend, WorkerBackendError,
)


class FakeBackend(WorkerBackend):
    def __init__(self, task=None):
        self.task = task
        self.reports = []
        self.claimed = []
        self.started = []
        self.fail_report = False

    def poll(self):
        task, self.task = self.task, None
        return task

    def claim(self, task):
        self.claimed.append(task["id"])

    def start(self, task):
        self.started.append(task["id"])

    def report(self, task, result, raw_error=""):
        if self.fail_report:
            raise WorkerBackendError("backend offline")
        self.reports.append((task["id"], result, raw_error))


class UncertainAdapter:
    def execute(self, task):
        raise DeviceUncertain("read-back timed out")


class FailingAdapter:
    def execute(self, task):
        raise DeviceFailure("reader rejected card")


def task():
    return {"id": "task-1", "task_type": "ISSUE_CARD", "payload": {}}


def test_successful_adapter_reports_once_after_claim_and_start():
    backend = FakeBackend(task())
    worker = TaskWorker(backend, MockAdapter("SUCCEEDED"), worker_id="worker-1", reader_id="reader-1")
    assert worker.process_once() is True
    assert backend.claimed == ["task-1"]
    assert backend.started == ["task-1"]
    assert backend.reports == [("task-1", "SUCCEEDED", "")]


def test_uncertain_device_outcome_is_unknown_not_failed():
    backend = FakeBackend(task())
    worker = TaskWorker(backend, UncertainAdapter(), worker_id="worker-1", reader_id="reader-1")
    worker.process_once()
    assert backend.reports == [("task-1", "UNKNOWN", "read-back timed out")]


def test_known_device_failure_is_failed_without_retry():
    backend = FakeBackend(task())
    worker = TaskWorker(backend, FailingAdapter(), worker_id="worker-1", reader_id="reader-1")
    worker.process_once()
    assert backend.reports == [("task-1", "FAILED", "reader rejected card")]
    assert backend.poll() is None


def test_result_report_outage_is_journaled_then_retried(tmp_path):
    backend = FakeBackend(task())
    backend.fail_report = True
    journal = tmp_path / "pending-result.json"
    worker = TaskWorker(backend, MockAdapter("UNKNOWN"), worker_id="worker-1",
                        reader_id="reader-1", journal_path=journal)
    with pytest.raises(WorkerBackendError):
        worker.process_once()
    assert json.loads(journal.read_text(encoding="utf-8"))["result"] == "UNKNOWN"

    backend.fail_report = False
    assert worker.process_once() is False
    assert backend.reports == [("task-1", "UNKNOWN", "mock uncertain result")]
    assert not journal.exists()


def test_empty_poll_does_nothing():
    backend = FakeBackend()
    worker = TaskWorker(backend, MockAdapter("SUCCEEDED"), worker_id="worker-1", reader_id="reader-1")
    assert worker.process_once() is False
    assert backend.reports == []
