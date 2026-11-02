from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.modules.common import new_id
from app.modules.wallet.models import LedgerEntry, MemberAccount


class WalletService:
    @staticmethod
    def _account(session: Session, member_id: str, *, lock: bool = False) -> MemberAccount:
        statement = select(MemberAccount).where(MemberAccount.member_id == member_id)
        if lock:
            statement = statement.with_for_update()
        account = session.scalar(statement)
        if account is None:
            raise ApiError(404, "WALLET_NOT_FOUND", "Member wallet not found")
        return account

    @staticmethod
    def available_cents(session: Session, member_id: str) -> int:
        account = WalletService._account(session, member_id)
        return account.principal_cents + account.gift_cents

    @staticmethod
    def _existing(session: Session, member_id: str, entry_type: str, reference: str,
                  *, lock: bool = False) -> LedgerEntry | None:
        statement = select(LedgerEntry).where(
            LedgerEntry.member_id == member_id,
            LedgerEntry.entry_type == entry_type,
            LedgerEntry.reference == reference,
        )
        if lock:
            statement = statement.with_for_update()
        return session.scalar(statement)

    @staticmethod
    def credit(
        session: Session, member_id: str, principal_cents: int, gift_cents: int,
        reference: str, entry_type: str = "RECHARGE",
    ) -> LedgerEntry:
        if principal_cents < 0 or gift_cents < 0 or principal_cents + gift_cents <= 0:
            raise ApiError(422, "INVALID_CREDIT", "Credit amounts must be nonnegative and nonzero in total")
        existing = WalletService._existing(session, member_id, entry_type, reference)
        if existing:
            return existing
        account = WalletService._account(session, member_id, lock=True)
        existing = WalletService._existing(session, member_id, entry_type, reference, lock=True)
        if existing:
            return existing
        account.principal_cents += principal_cents
        account.gift_cents += gift_cents
        entry = LedgerEntry(
            id=new_id("led"), member_id=member_id, entry_type=entry_type, reference=reference,
            principal_delta=principal_cents, gift_delta=gift_cents,
            principal_after=account.principal_cents, gift_after=account.gift_cents,
        )
        session.add(entry)
        session.flush()
        return entry

    @staticmethod
    def debit(session: Session, member_id: str, amount_cents: int, reference: str) -> LedgerEntry:
        if amount_cents <= 0:
            raise ApiError(422, "INVALID_DEBIT", "Debit amount must be positive")
        existing = WalletService._existing(session, member_id, "CONSUME", reference)
        if existing:
            return existing
        account = WalletService._account(session, member_id, lock=True)
        existing = WalletService._existing(session, member_id, "CONSUME", reference, lock=True)
        if existing:
            return existing
        principal = min(account.principal_cents, amount_cents)
        gift = amount_cents - principal
        if gift > account.gift_cents:
            raise ApiError(409, "INSUFFICIENT_BALANCE", "Insufficient member balance")
        account.principal_cents -= principal
        account.gift_cents -= gift
        entry = LedgerEntry(
            id=new_id("led"), member_id=member_id, entry_type="CONSUME", reference=reference,
            principal_delta=-principal, gift_delta=-gift,
            principal_after=account.principal_cents, gift_after=account.gift_cents,
        )
        session.add(entry)
        session.flush()
        return entry

    @staticmethod
    def refund(session: Session, member_id: str, original_reference: str, reference: str) -> LedgerEntry:
        existing = WalletService._existing(session, member_id, "REVERSAL", reference)
        if existing:
            return existing
        original = WalletService._existing(session, member_id, "CONSUME", original_reference)
        if original is None:
            raise ApiError(404, "ORIGINAL_DEBIT_NOT_FOUND", "Original wallet debit not found")
        account = WalletService._account(session, member_id, lock=True)
        existing = WalletService._existing(session, member_id, "REVERSAL", reference, lock=True)
        if existing:
            return existing
        original = WalletService._existing(session, member_id, "CONSUME", original_reference, lock=True)
        if original is None:
            raise ApiError(404, "ORIGINAL_DEBIT_NOT_FOUND", "Original wallet debit not found")
        principal = -original.principal_delta
        gift = -original.gift_delta
        account.principal_cents += principal
        account.gift_cents += gift
        entry = LedgerEntry(
            id=new_id("led"), member_id=member_id, entry_type="REVERSAL", reference=reference,
            principal_delta=principal, gift_delta=gift,
            principal_after=account.principal_cents, gift_after=account.gift_cents,
            original_entry_id=original.id,
        )
        session.add(entry)
        session.flush()
        return entry
