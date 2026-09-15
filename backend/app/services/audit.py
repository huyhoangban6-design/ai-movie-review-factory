"""SystemLog writer — structured app events (Phase 8, docs/03 `system_logs`).

Complements the Python `logging` emitted in the request middleware; DB rows are
written for events worth querying later (cost alerts, provider failures, budget
blocks). Uses the caller's session so transactionality is preserved.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.cost import SystemLog

log = logging.getLogger("app.audit")


def write_system_log(
    db: Session,
    *,
    level: str = "info",
    logger: str = "app",
    event: str = "log",
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    owner_id: int | None = None,
) -> SystemLog:
    if level == "error":
        log.error("%s %s: %s", logger, event, message)
    elif level == "warning":
        log.warning("%s %s: %s", logger, event, message)
    else:
        log.info("%s %s: %s", logger, event, message)

    row = SystemLog(
        owner_id=owner_id,
        level=level,
        logger=logger,
        event=event,
        message=message,
        details=details,
        request_id=request_id,
    )
    db.add(row)
    db.flush()
    return row