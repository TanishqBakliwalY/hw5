"""Append-only audit trail at output/audit_trail.json.

The file is a JSON array of AuditEvent objects. Each write reads the existing array,
appends, and atomically replaces the file -- earlier runs are never wiped. If the file
is ever unreadable it is moved aside (not deleted) and a new array is started.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from .config import AUDIT_TEXT_LIMIT, AUDIT_TRAIL, MODEL_NAME
from .models import AuditEvent, AuditLayer, TeamDeps

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    """Keep audit entries bounded: long strings are truncated, containers are clipped recursively."""
    if isinstance(value, str):
        return value if len(value) <= AUDIT_TEXT_LIMIT else value[:AUDIT_TEXT_LIMIT] + f"...[+{len(value) - AUDIT_TEXT_LIMIT} chars]"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clip(v) for v in value]
    return value


def _read_existing() -> list:
    if not AUDIT_TRAIL.exists() or AUDIT_TRAIL.stat().st_size == 0:
        return []
    try:
        data = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    AUDIT_TRAIL.replace(AUDIT_TRAIL.with_name(f"audit_trail.corrupt-{stamp}.json"))
    return []


def append(event: AuditEvent) -> None:
    with _lock:
        AUDIT_TRAIL.parent.mkdir(parents=True, exist_ok=True)
        events = _read_existing()
        events.append(event.model_dump(mode="json"))
        tmp = AUDIT_TRAIL.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_TRAIL)


def record_human(event: str, data: dict[str, Any], ticket_id: int | None = None) -> None:
    """Record an action taken by a person through the dashboard API (approve, deny, reset)."""
    append(
        AuditEvent(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            run_id="human",
            seq=0,
            layer="human",
            event=event,
            ticket_id=ticket_id,
            data=_clip(data),
        )
    )


def record(
    deps: TeamDeps,
    layer: AuditLayer,
    event: str,
    data: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    *,
    agent_level: bool = True,
) -> None:
    """Record one step for the agent described by `deps` (or a run-level event if agent_level=False)."""
    append(
        AuditEvent(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            run_id=deps.run.run_id,
            seq=deps.run.next_seq(),
            layer=layer,
            event=event,
            agent=deps.agent if agent_level else None,
            depth=deps.depth if agent_level else None,
            chain=list(deps.chain) if agent_level else [],
            ticket_id=deps.ticket_id,
            model=MODEL_NAME if layer == "llm" else None,
            data=_clip(data or {}),
            usage=usage,
        )
    )
