"""Campus Customs dashboard API (FastAPI).

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

Agents read and prepare work only through the MCP server. The routes here are the human
side: see tickets, start a team run, watch agent events, approve (or deny) the payments the
agents prepared, check cash, and reset the working database for a fresh run.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# `uvicorn main:app` runs this file as a top-level module from backend/, so put the
# project root on the path and import the agent team as the `backend` package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import audit, shop_db  # noqa: E402
from backend.config import (  # noqa: E402
    MAX_DELEGATION_DEPTH, MODEL_NAME, TEAM_REQUEST_LIMIT, TEAM_TOOL_CALLS_LIMIT, TEAM_TOTAL_TOKENS_LIMIT, WORKING_DB,
)
from backend.events import latest_runs_by_ticket, recent_events, requests_in_run  # noqa: E402
from backend.team import Team, new_run_id, ticket_task  # noqa: E402

app = FastAPI(
    title="Campus Customs Operations API",
    description="Human dashboard API for the Campus Customs multi-agent team.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(shop_db.ShopError)
async def _shop_error(_: Request, exc: shop_db.ShopError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, **exc.extra})


# --------------------------------------------------------------------------- team runs

# One team run at a time: every run shares the same cash, invoices and tickets.
RUNS: dict[str, dict[str, Any]] = {}
_current_run: str | None = None
_background: set[asyncio.Task] = set()  # keep references so running tasks are not garbage-collected


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def _execute_run(run_id: str, ticket_id: int) -> None:
    global _current_run
    rec = RUNS[run_id]
    try:
        async with Team() as team:
            report = await team.run_task(ticket_task(ticket_id), ticket_id=ticket_id, run_id=run_id)
        rec.update(status="completed", report=report.model_dump(mode="json"))
        # Tie the payments this run raised (or depends on) to the ticket, then resolve it if none is pending.
        linked = requests_in_run(run_id) | {
            h.payment_request_id
            for t in getattr(report, "tickets", []) if t.ticket_id == ticket_id
            for h in t.human_actions_needed if h.payment_request_id is not None
        }
        shop_db.link_requests(ticket_id, linked, run_id)
        rec["settle"] = shop_db.settle_ticket(ticket_id)
    except Exception as exc:  # the audit trail already has the details (run_failed)
        rec.update(status="failed", error=repr(exc))
        shop_db.reopen_after_failure(ticket_id, repr(exc))
    finally:
        rec["finished_at"] = _now()
        _current_run = None


class RunStarted(BaseModel):
    run_id: str
    ticket_id: int
    status: str
    events_url: str
    run_url: str


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(
    ticket_id: int,
    wait: bool = Query(False, description="true = block until the run finishes and return the report"),
) -> dict:
    """Run the agent team (starting with the Boss) on one ticket."""
    global _current_run
    if not shop_db.ticket_exists(ticket_id):
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if _current_run is not None:
        raise HTTPException(409, f"Run {_current_run} is still in progress; wait for it to finish.")

    run_id = new_run_id()
    _current_run = run_id
    RUNS[run_id] = {
        "run_id": run_id, "ticket_id": ticket_id, "status": "running", "model": MODEL_NAME,
        "started_at": _now(), "finished_at": None, "report": None, "error": None,
    }
    task = asyncio.create_task(_execute_run(run_id, ticket_id))
    _background.add(task)
    task.add_done_callback(_background.discard)
    if wait:
        await task
        return RUNS[run_id]
    return RunStarted(
        run_id=run_id, ticket_id=ticket_id, status="running",
        events_url=f"/api/events?run_id={run_id}", run_url=f"/api/runs/{run_id}",
    ).model_dump()


@app.get("/api/runs")
def list_runs() -> dict:
    """Runs started since the server came up (newest first)."""
    runs = sorted(RUNS.values(), key=lambda r: r["started_at"], reverse=True)
    return {"current_run": _current_run, "runs": [{k: v for k, v in r.items() if k != "report"} for r in runs]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    """Status of one run, and the Boss's final report once it has finished."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} in this server session (see /api/events for older runs).")
    return RUNS[run_id]


# --------------------------------------------------------------------------- tickets / events


LIMITS = {
    "requests": TEAM_REQUEST_LIMIT,
    "tool_calls": TEAM_TOOL_CALLS_LIMIT,
    "total_tokens": TEAM_TOTAL_TOKENS_LIMIT,
    "max_delegation_depth": MAX_DELEGATION_DEPTH,
}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": MODEL_NAME, "database": WORKING_DB.name, "current_run": _current_run, "limits": LIMITS}


@app.get("/api/tickets")
def tickets() -> dict:
    """All tickets with their status, whether each is open or resolved, linked payments and latest run."""
    data = shop_db.list_tickets()
    latest = latest_runs_by_ticket()
    for t in data["tickets"]:
        run = latest.get(t["id"])
        if run and run["status"] == "running" and run["run_id"] != _current_run:
            run = {**run, "status": "interrupted"}  # server restarted mid-run
        t["last_run"] = run
        t["running"] = run is not None and run["run_id"] == _current_run
    data["current_run"] = _current_run
    return data


class ResolveBody(BaseModel):
    resolved_by: str = Field(..., min_length=2)
    note: str = Field("", max_length=500)


@app.post("/api/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, body: ResolveBody) -> dict:
    """A human closes a ticket by hand (normally tickets resolve themselves once payments are decided)."""
    result = shop_db.resolve_manually(ticket_id, body.resolved_by, body.note)
    audit.record_human("ticket_resolved_manually", {"by": body.resolved_by, **result}, ticket_id=ticket_id)
    return result


def _settle_after_decision(request_id: int) -> list[dict]:
    return [shop_db.settle_ticket(t) for t in shop_db.tickets_for_request(request_id)]


@app.get("/api/events")
def events(
    after: int | None = Query(None, description="only events with id > after (use next_after from the last call)"),
    run_id: str | None = None,
    ticket_id: int | None = None,
    agent: str | None = None,
    limit: int = Query(200, ge=1, le=2000),
) -> dict:
    """Recent agent events from output/audit_trail.json: what each agent said and which tools it used."""
    return recent_events(after=after, run_id=run_id, ticket_id=ticket_id, agent=agent, limit=limit)


# --------------------------------------------------------------------------- money (human only)


class ApproveBody(BaseModel):
    approved_by: str = Field(..., min_length=2, description="Name of the human approving")


class DenyBody(BaseModel):
    decided_by: str = Field(..., min_length=2)
    reason: str = Field("", max_length=500)


@app.get("/api/payments")
def payments(status: str | None = None) -> dict:
    """Payment requests the agents prepared (filter with ?status=pending_approval)."""
    return shop_db.list_payment_requests(status)


@app.post("/api/payments/{request_id}/approve")
def approve(request_id: int, body: ApproveBody) -> dict:
    """A human approves an agent-prepared payment. This is the only route that changes cash."""
    try:
        result = shop_db.approve_payment(request_id, body.approved_by)
    except shop_db.ShopError as exc:
        cash_reject = exc.extra.get("status") == "rejected_insufficient_cash"
        audit.record_human("payment_rejected_insufficient_cash" if cash_reject else "payment_approve_failed",
                           {"request_id": request_id, "by": body.approved_by, "detail": exc.message})
        if cash_reject:
            _settle_after_decision(request_id)
        raise
    audit.record_human("payment_approved", {"by": body.approved_by, **result})
    result["tickets"] = _settle_after_decision(request_id)
    return result


@app.post("/api/payments/{request_id}/deny")
def deny(request_id: int, body: DenyBody) -> dict:
    """A human denies an agent-prepared payment (no money moves)."""
    result = shop_db.deny_payment(request_id, body.decided_by, body.reason)
    audit.record_human("payment_denied", {"by": body.decided_by, "reason": body.reason, "request_id": request_id})
    result["tickets"] = _settle_after_decision(request_id)
    return result


@app.get("/api/cash")
def cash() -> dict:
    """Current checking balance from cash_accounts (plus pending requests and payments made)."""
    return shop_db.get_cash()


@app.post("/api/reset")
def reset() -> dict:
    """Copy data/campus_customs.db over the working copy for a fresh run. The audit trail is kept."""
    if _current_run is not None:
        raise HTTPException(409, f"Run {_current_run} is in progress; reset after it finishes.")
    result = shop_db.reset()
    audit.record_human("database_reset", result)
    return result
