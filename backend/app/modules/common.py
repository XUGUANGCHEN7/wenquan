from datetime import UTC, datetime
from uuid import uuid4


def utcnow() -> datetime:
    """Naive UTC keeps SQLite and MySQL comparisons consistent."""
    return datetime.now(UTC).replace(tzinfo=None)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def new_business_no(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC):%Y%m%d%H%M%S}{uuid4().hex[:12].upper()}"
