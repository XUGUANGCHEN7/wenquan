from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.access.models import Card, CardBinding, Deposit, Locker, LockerReservation, Visit
from app.modules.audit import audit
from app.modules.common import new_business_no, new_id, utcnow
from app.modules.devices.models import DeviceTask

TERMINAL_RESULTS = {"SUCCEEDED", "FAILED", "UNKNOWN"}


class DeviceService:
    @staticmethod
    def create_task(session: Session, *, task_type: str, idempotency_key: str, operator: str,
                    binding_id: str | None = None, card_id: str | None = None,
                    locker_id: str | None = None, room_id: str | None = None,
                    payload: dict | None = None) -> DeviceTask:
        existing = session.scalar(select(DeviceTask).where(DeviceTask.idempotency_key == idempotency_key))
        if existing:
            return existing
        task = DeviceTask(id=new_id("tsk"), task_no=new_business_no("DT"), task_type=task_type,
                          idempotency_key=idempotency_key, operator=operator, binding_id=binding_id,
                          card_id=card_id, locker_id=locker_id, room_id=room_id, payload=payload or {})
        session.add(task)
        session.flush()
        return task

    @staticmethod
    def poll(session: Session, *, worker_id: str, reader_id: str) -> DeviceTask | None:
        return session.scalar(select(DeviceTask).where(DeviceTask.status == "PENDING")
                              .order_by(DeviceTask.created_at).limit(1).with_for_update(skip_locked=True))

    @staticmethod
    def claim(session: Session, task_id: str, *, worker_id: str, reader_id: str) -> DeviceTask:
        task = session.get(DeviceTask, task_id, with_for_update=True)
        if task is None:
            raise ApiError(404, "DEVICE_TASK_NOT_FOUND", "Device task not found")
        if task.status == "CLAIMED" and task.worker_id == worker_id:
            return task
        if task.status != "PENDING":
            raise ApiError(409, "DEVICE_TASK_NOT_CLAIMABLE", "Device task cannot be claimed")
        task.status = "CLAIMED"
        task.worker_id = worker_id
        task.reader_id = reader_id
        task.claimed_at = utcnow()
        session.flush()
        return task

    @staticmethod
    def start(session: Session, task_id: str, *, worker_id: str) -> DeviceTask:
        task = session.get(DeviceTask, task_id, with_for_update=True)
        if task is None or task.status != "CLAIMED" or task.worker_id != worker_id:
            raise ApiError(409, "DEVICE_TASK_NOT_STARTABLE", "Only the claiming worker can start this task")
        task.status = "RUNNING"
        session.flush()
        return task

    @staticmethod
    def report(session: Session, task_id: str, *, worker_id: str, result: str,
               raw_error: str = "") -> DeviceTask:
        task = session.get(DeviceTask, task_id, with_for_update=True)
        if task is None or task.worker_id != worker_id:
            raise ApiError(404, "DEVICE_TASK_NOT_FOUND", "Device task not found for this worker")
        if result not in TERMINAL_RESULTS:
            raise ApiError(422, "DEVICE_RESULT_INVALID", "Unsupported device result")
        if task.status in TERMINAL_RESULTS:
            if task.status == result and task.raw_error == raw_error:
                return task
            raise ApiError(409, "DEVICE_RESULT_CONFLICT", "A different terminal result was already recorded")
        if task.status != "RUNNING":
            raise ApiError(409, "DEVICE_TASK_NOT_RUNNING", "Device task must be running before completion")
        before = task.status
        task.status = result
        task.raw_error = raw_error
        task.completed_at = utcnow()
        DeviceService._apply_result(session, task, result)
        audit(session, actor=worker_id, action="DEVICE_TASK_RESULT", entity_type="device_task",
              entity_id=task.id, before=before, after=result, reason=raw_error,
              request_id=f"device-{task.task_no}"[:64])
        session.flush()
        return task

    @staticmethod
    def _apply_result(session: Session, task: DeviceTask, result: str) -> None:
        if task.task_type == "EXTEND_ROOM":
            from app.modules.rooms.extension import RoomExtensionService

            RoomExtensionService.apply_device_result(session, task, result)
            return
        binding = session.get(CardBinding, task.binding_id, with_for_update=True) if task.binding_id else None
        if binding is None:
            return
        card = session.get(Card, binding.card_id, with_for_update=True)
        locker = session.get(Locker, binding.locker_id, with_for_update=True)
        if task.task_type == "ISSUE_CARD" and result == "SUCCEEDED":
            binding.status = "BOUND"
            binding.bound_at = utcnow()
            card.status = "BOUND"
            locker.status = "BOUND"
            reservation = session.scalar(select(LockerReservation).where(LockerReservation.binding_id == binding.id))
            reservation.status = "CONFIRMED"
            visit = session.get(Visit, binding.visit_id)
            visit.status = "ISSUED"
            # Admission remains a separate, explicit front-desk action. A write/read-back
            # result must not silently consume a paid ticket if the wrong card was selected.
        elif task.task_type == "CLEAR_CARD":
            if result == "SUCCEEDED":
                card.status = "AVAILABLE"
                binding.status = "CLEARED"
            elif result == "FAILED":
                card.status = "QUARANTINED"
                binding.status = "CLEAR_FAILED"
