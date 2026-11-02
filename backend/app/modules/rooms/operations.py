from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, Role, require_roles
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.access.models import CardBinding
from app.modules.common import new_id, utcnow
from app.modules.devices.models import DeviceTask
from app.modules.devices.router import task_dict
from app.modules.rooms.extension import RoomExtensionService
from app.modules.rooms.models import PrivateBooking, Room, RoomBlock, RoomUse
from app.modules.rooms.service import RoomService

router = APIRouter(prefix="/api/v1/operations/rooms", tags=["operations-rooms"])
DeskAuth = Annotated[AuthContext, Depends(require_roles(Role.FRONTDESK, Role.ADMIN))]


class AssignRequest(BaseModel):
    actual_start: datetime
    reason: str = Field(min_length=1, max_length=500)
    binding_id: str | None = None


class ReasonRequest(BaseModel):
    reason: str = Field(default="Operator confirmed", max_length=500)


class BlockRequest(BaseModel):
    room_id: str
    start_at: datetime
    end_at: datetime
    kind: Literal["MAINTENANCE", "MANUAL"]
    reason: str = Field(min_length=1, max_length=500)


class ExtensionRequest(BaseModel):
    binding_id: str


@router.get("/board")
def board(auth: DeskAuth, session: Session = Depends(get_db)):
    rooms = session.scalars(select(Room).order_by(Room.number)).all()
    result = []
    now = utcnow()
    for room in rooms:
        use = session.scalar(select(RoomUse).where(RoomUse.room_id == room.id, RoomUse.status != "COMPLETED")
                             .order_by(RoomUse.actual_start_at.desc()).limit(1))
        block = session.scalar(select(RoomBlock).where(RoomBlock.room_id == room.id,
                                                       RoomBlock.start_at <= now, RoomBlock.end_at > now).limit(1))
        status = "MAINTENANCE" if block else (use.status if use else ("FREE" if room.active else "MAINTENANCE"))
        result.append({"id": room.id, "number": room.number, "status": status,
                       "room_use_id": use.id if use else None, "booking_id": use.booking_id if use else None,
                       "actual_end_at": use.actual_end_at if use else None,
                       "cleaning_end_at": use.cleaning_end_at if use else None})
    return result


@router.post("/bookings/{booking_id}/assign")
def assign(booking_id: str, payload: AssignRequest, request: Request,
           auth: DeskAuth, session: Session = Depends(get_db)):
    use = RoomService.assign_booking(session, booking_id, actual_start=payload.actual_start,
                                     operator=auth.role, reason=payload.reason,
                                     request_id=request.state.request_id)
    if use is None:
        session.commit()
        raise ApiError(409, "ASSIGNMENT_CONFLICT", "No room can cover the delayed use and cleaning interval")
    if payload.binding_id:
        binding = session.get(CardBinding, payload.binding_id, with_for_update=True)
        if binding is None or binding.status != "BOUND":
            raise ApiError(409, "WRISTBAND_NOT_VALID", "A bound wristband is required")
        binding.room_use_id = use.id
    session.commit()
    return {"room_use_id": use.id, "room_number": use.room.number, "status": use.status,
            "actual_end_at": use.actual_end_at, "cleaning_end_at": use.cleaning_end_at}


@router.post("/uses/{room_use_id}/finish")
def finish(room_use_id: str, payload: ReasonRequest, request: Request,
           auth: DeskAuth, session: Session = Depends(get_db)):
    use = RoomService.finish_use(session, room_use_id, operator=auth.role, reason=payload.reason,
                                 request_id=request.state.request_id)
    session.commit()
    return {"room_use_id": use.id, "status": use.status}


@router.post("/uses/{room_use_id}/cleaning/start")
def cleaning_start(room_use_id: str, request: Request, auth: DeskAuth, session: Session = Depends(get_db)):
    record = RoomService.start_cleaning(session, room_use_id, operator=auth.role,
                                        request_id=request.state.request_id)
    session.commit()
    return {"room_use_id": room_use_id, "status": "CLEANING", "started_at": record.started_at}


@router.post("/uses/{room_use_id}/cleaning/complete")
def cleaning_complete(room_use_id: str, request: Request, auth: DeskAuth, session: Session = Depends(get_db)):
    record = RoomService.complete_cleaning(session, room_use_id, operator=auth.role,
                                           request_id=request.state.request_id)
    session.commit()
    return {"room_use_id": room_use_id, "status": "COMPLETED", "completed_at": record.completed_at}


@router.post("/blocks", status_code=201)
def create_block(payload: BlockRequest, request: Request, auth: DeskAuth,
                 session: Session = Depends(get_db)):
    if payload.end_at <= payload.start_at:
        raise ApiError(422, "BLOCK_INTERVAL_INVALID", "Block end must be after start")
    block = RoomBlock(id=new_id("blk"), **payload.model_dump())
    session.add(block)
    from app.modules.audit import audit

    audit(session, actor=auth.role, action="ROOM_BLOCK_CREATED", entity_type="room_block",
          entity_id=block.id, before=None, after="RECORDED", reason=payload.reason,
          request_id=request.state.request_id)
    session.commit()
    return {"id": block.id, "status": "RECORDED"}


@router.post("/uses/{room_use_id}/extensions", status_code=201)
def create_extension(room_use_id: str, payload: ExtensionRequest, request: Request,
                     auth: DeskAuth, session: Session = Depends(get_db)):
    extension, order = RoomExtensionService.create(session, room_use_id=room_use_id,
                                                   binding_id=payload.binding_id, operator=auth.role)
    from app.modules.audit import audit

    audit(session, actor=auth.role, action="ROOM_EXTENSION_REQUESTED", entity_type="room_extension",
          entity_id=extension.id, before=None, after=extension.status, reason="Front desk extension",
          request_id=request.state.request_id)
    session.commit()
    task = session.scalar(select(DeviceTask).where(DeviceTask.idempotency_key == f"extend-{extension.id}"))
    return {"extension_id": extension.id, "order_no": order.order_no, "amount_cents": order.amount_cents,
            "status": extension.status, "task": task_dict(task) if task else None}
