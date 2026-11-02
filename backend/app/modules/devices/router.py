from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.modules.devices.models import DeviceTask
from app.modules.devices.service import DeviceService

router = APIRouter(prefix="/api/v1/devices/tasks", tags=["devices"])
DeviceAuth = Annotated[AuthContext, Depends(require_roles(Role.DEVICE))]


class PollRequest(BaseModel):
    worker_id: str
    reader_id: str


class StartRequest(BaseModel):
    worker_id: str


class ResultRequest(BaseModel):
    worker_id: str
    result: Literal["SUCCEEDED", "FAILED", "UNKNOWN"]
    raw_error: str = ""


def task_dict(task: DeviceTask) -> dict:
    return {"id": task.id, "task_no": task.task_no, "task_type": task.task_type, "status": task.status,
            "binding_id": task.binding_id, "card_id": task.card_id, "locker_id": task.locker_id,
            "room_id": task.room_id, "payload": task.payload, "raw_error": task.raw_error,
            "version": task.version}


@router.post("/poll")
def poll(payload: PollRequest, auth: DeviceAuth, session: Session = Depends(get_db)):
    task = DeviceService.poll(session, **payload.model_dump())
    return task_dict(task) if task else None


@router.post("/{task_id}/claim")
def claim(task_id: str, payload: PollRequest, auth: DeviceAuth, session: Session = Depends(get_db)):
    task = DeviceService.claim(session, task_id, **payload.model_dump())
    session.commit()
    return task_dict(task)


@router.post("/{task_id}/start")
def start(task_id: str, payload: StartRequest, auth: DeviceAuth, session: Session = Depends(get_db)):
    task = DeviceService.start(session, task_id, worker_id=payload.worker_id)
    session.commit()
    return task_dict(task)


@router.post("/{task_id}/result")
def result(task_id: str, payload: ResultRequest, auth: DeviceAuth, session: Session = Depends(get_db)):
    task = DeviceService.report(session, task_id, **payload.model_dump())
    session.commit()
    return task_dict(task)
