"""Human-side database actions for the dashboard API.

Agents never use this module -- they read and prepare work only through the MCP server.
This is where a *person's* decision is applied: approving a payment request is the
only path that moves money (cash_accounts, payments, invoices). Everything works on the
working copy data/campus_customs_new.db; the original is only read by reset().
"""

from __future__ import annotations

import calendar
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any

from .agents.base import AGENT_NAMES
from .config import ORIGINAL_DB, WORKING_DB

CASH_ACCOUNT = "checking"


class ShopError(Exception):
    """A request the API should refuse; `status` is the HTTP status code to return."""

    def __init__(self, status: int, message: str, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra or {}


@contextmanager
def _connect(write: bool = False) -> Iterator[sqlite3.Connection]:
    if not WORKING_DB.exists():
        raise ShopError(503, "Working database is missing. POST /api/reset to create it from the original.")
    conn = sqlite3.connect(WORKING_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        if write:
            conn.execute("BEGIN IMMEDIATE")  # one writer at a time, so two approvals can't race
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _ensure_desk_tables(conn: sqlite3.Connection) -> None:
    """Tables the desk (human side) writes to. Same ticket_events schema the MCP server uses."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ticket_payment_links (
            ticket_id INTEGER NOT NULL,
            request_id INTEGER NOT NULL,
            run_id TEXT,
            PRIMARY KEY (ticket_id, request_id)
        );
        CREATE TABLE IF NOT EXISTS ticket_events (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            actor TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            note TEXT,
            shop_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _add_month(day: str) -> str:
    d = date.fromisoformat(day)
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1])).isoformat()


# --------------------------------------------------------------------------- reads


def list_tickets() -> dict:
    with _connect() as conn:
        today = _today(conn)
        tickets = [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id")]
        requests = (
            [dict(r) for r in conn.execute("SELECT * FROM payment_requests ORDER BY id")]
            if _has_table(conn, "payment_requests") else []
        )
        links = (
            {(r["ticket_id"], r["request_id"]) for r in conn.execute("SELECT * FROM ticket_payment_links")}
            if _has_table(conn, "ticket_payment_links") else set()
        )
    for t in tickets:
        t["state"] = "resolved" if t["status"] == "resolved" else "open"
        # A request belongs to a ticket if a run linked it, or it pays the ticket's own invoice/lease.
        t["payment_requests"] = [
            r for r in requests
            if (t["id"], r["id"]) in links
            or (r["kind"] == "invoice" and r["ref_id"] == t["invoice_id"])
            or (r["kind"] == "rent" and r["ref_id"] == t["lease_id"])
        ]
        t["pending_approvals"] = sum(r["status"] == "pending_approval" for r in t["payment_requests"])
    return {
        "date_today": today,
        "open_count": sum(t["state"] == "open" for t in tickets),
        "resolved_count": sum(t["state"] == "resolved" for t in tickets),
        "tickets": tickets,
    }


def ticket_exists(ticket_id: int) -> bool:
    with _connect() as conn:
        return conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is not None


def get_cash() -> dict:
    with _connect() as conn:
        acct = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (CASH_ACCOUNT,)
        ).fetchone()
        if acct is None:
            raise ShopError(404, f"No '{CASH_ACCOUNT}' row in cash_accounts.")
        pending = (
            conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total "
                "FROM payment_requests WHERE status = 'pending_approval'"
            ).fetchone()
            if _has_table(conn, "payment_requests") else {"n": 0, "total": 0}
        )
        paid = conn.execute(
            "SELECT id, kind, ref_id, amount, account, paid_at, approved_by FROM payments ORDER BY id"
        ).fetchall()
        today = _today(conn)
    return {
        "date_today": today,
        "account": acct["name"],
        "balance": acct["balance"],
        "balance_as_of": acct["date"],
        "pending_requests": pending["n"],
        "pending_total": pending["total"],
        "available_after_pending": acct["balance"] - pending["total"],
        "payments": [dict(p) for p in paid],
    }


def list_payment_requests(status: str | None = None) -> dict:
    with _connect() as conn:
        if not _has_table(conn, "payment_requests"):
            return {"count": 0, "requests": []}
        sql, args = "SELECT * FROM payment_requests", ()
        if status:
            sql, args = sql + " WHERE status = ?", (status,)
        rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", args)]
    return {"count": len(rows), "requests": rows}


# --------------------------------------------------------------------------- human decisions


def _check_human(name: str) -> str:
    name = name.strip()
    if len(name) < 2:
        raise ShopError(422, "A human approver name is required.")
    if name.lower() in AGENT_NAMES:
        raise ShopError(403, "Agents cannot approve or deny payments; a human must.")
    return name


def _load_pending(conn: sqlite3.Connection, request_id: int) -> sqlite3.Row:
    if not _has_table(conn, "payment_requests"):
        raise ShopError(404, f"No payment request {request_id}.")
    req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
    if req is None:
        raise ShopError(404, f"No payment request {request_id}.")
    if req["status"] != "pending_approval":
        raise ShopError(409, f"Payment request {request_id} is already '{req['status']}'.", {"request": dict(req)})
    return req


def approve_payment(request_id: int, approved_by: str) -> dict:
    """Pay an agent-prepared request after a human approves it. The only code path that changes cash."""
    approver = _check_human(approved_by)
    rejected: dict | None = None
    with _connect(write=True) as conn:
        req = _load_pending(conn, request_id)
        today = _today(conn)
        acct = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (CASH_ACCOUNT,)
        ).fetchone()
        balance = acct["balance"]
        amount = req["amount"]

        if amount > balance:
            # Shop rule: a payment is rejected if there isn't enough cash.
            conn.execute(
                "UPDATE payment_requests SET status = 'rejected_insufficient_cash', decided_by = ?, "
                "decided_at = ? WHERE id = ?",
                (approver, today, request_id),
            )
            rejected = {"request_id": request_id, "amount": amount, "balance": balance}
        else:
            effects: list[str] = []
            if req["kind"] == "invoice":
                inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
                if inv is None or inv["status"] != "open":
                    raise ShopError(409, f"Invoice {req['ref_id']} is no longer open; nothing to pay.")
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
                effects.append(f"invoice {req['ref_id']} marked paid (vendor hold lifted if no other open invoices)")
            elif req["kind"] == "rent":
                lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
                new_due = _add_month(lease["next_due"])
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, req["ref_id"]))
                effects.append(f"lease {req['ref_id']} next_due moved {lease['next_due']} -> {new_due}")

            new_balance = balance - amount
            conn.execute(
                "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                (new_balance, today, CASH_ACCOUNT),
            )
            cur = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (req["kind"], req["ref_id"], amount, CASH_ACCOUNT, today, approver),
            )
            conn.execute(
                "UPDATE payment_requests SET status = 'approved', decided_by = ?, decided_at = ? WHERE id = ?",
                (approver, today, request_id),
            )
            payment = dict(conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone())
            result = {
                "approved": True,
                "request_id": request_id,
                "payment": payment,
                "payee": req["payee"],
                "balance_before": balance,
                "balance_after": new_balance,
                "effects": effects,
            }

    if rejected:
        raise ShopError(
            409,
            f"Rejected: ${rejected['amount']:.2f} exceeds the ${rejected['balance']:.2f} checking balance.",
            {"request_id": request_id, "status": "rejected_insufficient_cash"},
        )
    return result


def deny_payment(request_id: int, decided_by: str, reason: str) -> dict:
    who = _check_human(decided_by)
    with _connect(write=True) as conn:
        _load_pending(conn, request_id)
        today = _today(conn)
        conn.execute(
            "UPDATE payment_requests SET status = 'denied', decided_by = ?, decided_at = ?, "
            "reason = COALESCE(reason, '') || ' | denied: ' || ? WHERE id = ?",
            (who, today, reason, request_id),
        )
        req = dict(conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone())
    return {"denied": True, "request": req}


def reset() -> dict:
    """Copy the original database over the working copy (the original is only read)."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return {"reset": True, "working_db": WORKING_DB.name, "copied_from": ORIGINAL_DB.name}


# --------------------------------------------------------------------------- ticket <-> payment links


DECIDED = {"approved", "denied", "rejected_insufficient_cash"}


def link_requests(ticket_id: int, request_ids: set[int], run_id: str) -> None:
    """Remember which payment requests a ticket's run raised or depends on."""
    with _connect(write=True) as conn:
        _ensure_desk_tables(conn)
        for rid in request_ids:
            conn.execute(
                "INSERT OR IGNORE INTO ticket_payment_links (ticket_id, request_id, run_id) VALUES (?, ?, ?)",
                (ticket_id, rid, run_id),
            )


def tickets_for_request(request_id: int) -> list[int]:
    with _connect() as conn:
        if not _has_table(conn, "ticket_payment_links"):
            return []
        return [r["ticket_id"] for r in conn.execute(
            "SELECT ticket_id FROM ticket_payment_links WHERE request_id = ?", (request_id,)
        )]


def _set_status(conn: sqlite3.Connection, ticket_id: int, new_status: str, actor: str, note: str) -> dict:
    _ensure_desk_tables(conn)
    old = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()["status"]
    conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    conn.execute(
        "INSERT INTO ticket_events (ticket_id, actor, old_status, new_status, note, shop_date, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (ticket_id, actor, old, new_status, note, _today(conn)),
    )
    return {"ticket_id": ticket_id, "old_status": old, "new_status": new_status, "note": note}


def settle_ticket(ticket_id: int) -> dict:
    """Resolve a ticket once its team run is done and every payment request linked to it is decided.

    Called after a run finishes and after each human approve/deny. A ticket with a pending
    request stays 'waiting_on_human' until a person decides it.
    """
    with _connect(write=True) as conn:
        _ensure_desk_tables(conn)
        t = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None or t["status"] == "resolved":
            return {"ticket_id": ticket_id, "resolved": t is not None, "changed": False}
        rows = conn.execute(
            "SELECT pr.id, pr.status FROM ticket_payment_links l "
            "JOIN payment_requests pr ON pr.id = l.request_id WHERE l.ticket_id = ?",
            (ticket_id,),
        ).fetchall() if _has_table(conn, "payment_requests") else []
        pending = [r["id"] for r in rows if r["status"] not in DECIDED]
        if pending:
            if t["status"] != "waiting_on_human":
                _set_status(conn, ticket_id, "waiting_on_human", "desk",
                            f"Waiting on human decision for payment request(s) {pending}.")
            return {"ticket_id": ticket_id, "resolved": False, "pending_requests": pending, "changed": False}
        decided = ", ".join(f"#{r['id']} {r['status']}" for r in rows) or "no payments needed"
        change = _set_status(conn, ticket_id, "resolved", "desk",
                             f"Team run finished and payments decided ({decided}).")
    return {"ticket_id": ticket_id, "resolved": True, "changed": True, **change}


def resolve_manually(ticket_id: int, by: str, note: str) -> dict:
    """A human closes a ticket by hand (e.g. after handling a decision outside the payment flow)."""
    who = _check_human(by)
    with _connect(write=True) as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            raise ShopError(404, f"No ticket {ticket_id}.")
        return _set_status(conn, ticket_id, "resolved", "desk", f"Closed by {who}: {note}".strip())


def reopen_after_failure(ticket_id: int, error: str) -> None:
    """A failed run must not leave a ticket looking like the team is still on it."""
    with _connect(write=True) as conn:
        t = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is not None and t["status"] == "in_progress":
            _set_status(conn, ticket_id, "open", "desk", f"Team run failed ({error[:120]}); ticket reopened.")
