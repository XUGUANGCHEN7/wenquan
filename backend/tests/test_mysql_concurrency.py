import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.mysql

MYSQL_URL = os.environ.get("WENQUAN_TEST_MYSQL_URL")


@pytest.fixture(scope="module")
def engine():
    if not MYSQL_URL:
        pytest.skip("Set WENQUAN_TEST_MYSQL_URL to run MySQL concurrency tests")
    from app.models import Base

    test_engine = create_engine(MYSQL_URL, pool_pre_ping=True, pool_size=6, max_overflow=6)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    from app.modules.seed import seed_development_data

    with factory() as session:
        seed_development_data(session)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_last_available_room_is_sold_only_once(engine):
    from app.core.errors import ApiError
    from app.modules.rooms.models import PrivateBooking, Room, RoomBlock
    from app.modules.rooms.service import RoomService

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    visit_date = date.today() + timedelta(days=40)
    with factory() as session:
        rooms = session.scalars(select(Room).order_by(Room.number)).all()
        for room in rooms[1:]:
            session.add(RoomBlock(id=f"concurrency-block-{room.id}", room_id=room.id,
                                  start_at=datetime.combine(visit_date, datetime.min.time()),
                                  end_at=datetime.combine(visit_date + timedelta(days=1), datetime.min.time()),
                                  reason="leave exactly one room", kind="MANUAL"))
        session.commit()

    barrier = Barrier(2)

    def hold_one():
        with factory() as session:
            barrier.wait()
            try:
                booking, _ = RoomService.create_booking(
                    session, member_id="member-demo", visit_date=visit_date, slot_indices=[0],
                    expected_arrival_at=datetime.combine(visit_date, datetime.min.time()),
                )
                session.commit()
                return booking.id
            except ApiError as exc:
                session.rollback()
                return exc.code
            except Exception as exc:
                session.rollback()
                return type(exc).__name__

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: hold_one(), range(2)))
    with factory() as session:
        count = session.scalar(select(func.count(PrivateBooking.id)).where(
            PrivateBooking.visit_date == visit_date, PrivateBooking.status.in_(["HELD", "CONFIRMED", "IN_USE"])))
    assert count == 1
    assert sum(1 for result in results if result.startswith("bkg_")) == 1
    assert "NO_ROOM_AVAILABLE" in results


def test_same_recharge_reference_is_credited_once_under_concurrency(engine):
    from app.modules.identity.models import Member
    from app.modules.wallet.models import LedgerEntry, MemberAccount
    from app.modules.wallet.service import WalletService

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(Member(id="member-concurrent", nickname="并发测试"))
        session.add(MemberAccount(member_id="member-concurrent"))
        session.commit()

    barrier = Barrier(2)

    def credit_once():
        with factory() as session:
            barrier.wait()
            try:
                WalletService.credit(session, "member-concurrent", 10_000, 0, "same-payment-callback")
                session.commit()
                return "ok"
            except Exception as exc:
                session.rollback()
                return type(exc).__name__

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: credit_once(), range(2)))
    with factory() as session:
        account = session.get(MemberAccount, "member-concurrent")
        entries = session.scalar(select(func.count(LedgerEntry.id)).where(
            LedgerEntry.member_id == "member-concurrent"))
    assert results == ["ok", "ok"]
    assert account.principal_cents == 10_000
    assert entries == 1
