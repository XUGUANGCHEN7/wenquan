"""Import all domain models here so metadata and Alembic see every table."""

from app.core.database import Base
from app.modules.access.models import Card, CardBinding, Deposit, DepositGroup, Locker, LockerReservation, Visit
from app.modules.catalog.models import BusinessConfig, RechargeActivity, TicketPriceRule
from app.modules.devices.models import DeviceTask
from app.modules.dining.models import FoodOrder, FoodOrderItem, MenuItem, Merchant, RoomQrCode
from app.modules.identity.models import Identity, Member
from app.modules.payments.models import AuditEvent, Order, Payment, Refund
from app.modules.rooms.models import CleaningRecord, PrivateBooking, Room, RoomBlock, RoomExtension, RoomUse
from app.modules.tickets.models import Admission, Ticket, TicketBatch
from app.modules.wallet.models import LedgerEntry, MemberAccount

__all__ = [
    "Base", "AuditEvent", "BusinessConfig", "Identity", "LedgerEntry", "Member",
    "MemberAccount", "Order", "Payment", "RechargeActivity", "Refund", "TicketPriceRule",
]
