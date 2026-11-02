from sqlalchemy.orm import Session

from app.modules.common import new_id
from app.modules.payments.models import AuditEvent


def audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: str | None,
    after: str | None,
    reason: str,
    request_id: str,
) -> AuditEvent:
    event = AuditEvent(
        id=new_id("aud"), actor=actor, action=action, entity_type=entity_type,
        entity_id=entity_id, before_status=before, after_status=after,
        reason=reason, request_id=request_id,
    )
    session.add(event)
    return event
