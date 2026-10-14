"""Turn output/audit_trail.json into a feed the dashboard can poll.

Each audit event becomes a flat row with a stable `id` (its position in the append-only
file), so the board can ask for "everything after id N" on each refresh.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from .config import AUDIT_TRAIL


def _short(value: Any, limit: int = 240) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarize_output(output: dict) -> str | None:
    if not output:
        return None
    if "tickets" in output:  # BossReport
        parts = [f"#{t['ticket_id']} {t['status']}: {t['summary']}" for t in output.get("tickets", [])]
        return " | ".join(parts) or output.get("cash_summary")
    return output.get("summary")


def _row(index: int, e: dict) -> dict:
    d = e.get("data") or {}
    ev = e["event"]
    meta: dict[str, Any] = {}  # structured bits the board renders (tool chips, hand-offs, reports)
    said: str | None = None
    tools: list[str] = []
    text = ev

    if ev == "model_response":
        parts = d.get("parts", [])
        said = "\n".join(p["content"] for p in parts if p.get("type") == "text") or None
        tools = [p["tool"] for p in parts if p.get("type") == "tool_call" and p["tool"] != "final_result"]
        if any(p.get("type") == "tool_call" and p["tool"] == "final_result" for p in parts):
            text = "returned its final report"
        elif tools:
            text = "decided to call " + ", ".join(tools)
        else:
            text = "replied"
    elif ev == "model_request":
        kinds = Counter(p.get("type") for p in d.get("parts", []))
        text = f"model request (step {d.get('step')}): " + ", ".join(f"{k}×{n}" for k, n in kinds.items())
    elif ev == "tool_call":
        tools = [d.get("tool")]
        meta = {"tool": d.get("tool"), "tool_call_id": d.get("tool_call_id"), "args": d.get("args")}
        text = f"{d.get('tool')}({_short(d.get('args', {}), 160)})"
    elif ev == "tool_result":
        meta = {"tool": d.get("tool"), "tool_call_id": d.get("tool_call_id"), "ms": d.get("ms")}
        text = f"{d.get('tool')} → {_short(d.get('result'))} ({d.get('ms')} ms)"
    elif ev == "tool_error":
        text = f"{d.get('tool')} failed: {_short(d.get('error'))}"
    elif ev == "delegation_start":
        tools = ["delegate"]
        meta = {"to_agent": d.get("to_agent"), "task": d.get("task"), "reason": d.get("reason")}
        text = f"→ {d.get('to_agent')}: {_short(d.get('task'))}"
    elif ev == "delegation_result":
        text = f"← {d.get('to_agent')} reported: {_short((d.get('report') or {}).get('summary', ''))}"
    elif ev == "delegation_refused":
        meta = {"to_agent": d.get("to_agent"), "why": d.get("why")}
        text = f"delegation to {d.get('to_agent')} refused: {d.get('why')}"
    elif ev == "agent_start":
        meta = {"task": d.get("task")}
        text = f"started: {_short(d.get('task'))}"
    elif ev == "agent_end":
        said = _summarize_output(d.get("output") or {})
        meta = {"output": d.get("output"), "steps": d.get("steps")}
        text = f"finished in {d.get('steps')} steps"
    elif ev == "agent_error":
        text = f"error: {_short(d.get('error'))}"
    elif ev in ("run_start", "run_end", "run_failed"):
        text = {"run_start": f"run started: {_short(d.get('task'))}",
                "run_end": "run finished",
                "run_failed": f"run failed: {_short(d.get('error'))}"}[ev]
    elif e.get("layer") == "human":
        text = f"human: {ev} {_short(d)}"

    return {
        "id": index,
        "ts": e.get("ts"),
        "run_id": e.get("run_id"),
        "seq": e.get("seq"),
        "layer": e.get("layer"),
        "event": ev,
        "agent": e.get("agent"),
        "depth": e.get("depth"),
        "ticket_id": e.get("ticket_id"),
        "text": text,
        "said": said,
        "tools": tools,
        "usage": e.get("usage"),
        "meta": meta,
    }


def _load() -> list[dict]:
    if not AUDIT_TRAIL.exists() or AUDIT_TRAIL.stat().st_size == 0:
        return []
    try:
        data = json.loads(AUDIT_TRAIL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def recent_events(
    *,
    after: int | None = None,
    run_id: str | None = None,
    ticket_id: int | None = None,
    agent: str | None = None,
    limit: int = 200,
) -> dict:
    raw = _load()
    rows = []
    start = 0 if after is None else after + 1
    for i in range(start, len(raw)):
        e = raw[i]
        if run_id and e.get("run_id") != run_id:
            continue
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            continue
        if agent and e.get("agent") != agent:
            continue
        rows.append(_row(i, e))
    rows = rows[-limit:]

    by_agent: dict[str, dict[str, Any]] = defaultdict(lambda: {"said": [], "tools": Counter()})
    for r in rows:
        if not r["agent"]:
            continue
        if r["said"]:
            by_agent[r["agent"]]["said"].append(r["said"])
        if r["event"] in ("tool_call", "delegation_start"):  # executed calls only, not the model's intent
            for t in r["tools"]:
                by_agent[r["agent"]]["tools"][t] += 1
    agents = {
        a: {"said": v["said"][-5:], "tools_used": dict(v["tools"])} for a, v in by_agent.items()
    }
    return {
        "total_events": len(raw),
        "next_after": len(raw) - 1,  # pass back as ?after= to get only newer events
        "count": len(rows),
        "events": rows,
        "agents": agents,
    }


def requests_in_run(run_id: str) -> set[int]:
    """Payment request ids that request_payment returned during a run (new or existing duplicate)."""
    ids: set[int] = set()
    for e in _load():
        if e.get("run_id") != run_id or e.get("event") != "tool_result":
            continue
        d = e.get("data") or {}
        if d.get("tool") != "request_payment" or not isinstance(d.get("result"), dict):
            continue
        req = d["result"].get("request") or {}
        if isinstance(req.get("id"), int):
            ids.add(req["id"])
    return ids


def latest_runs_by_ticket() -> dict[int, dict[str, Any]]:
    """For each ticket, the most recent team run recorded in the audit trail."""
    runs: dict[str, dict[str, Any]] = {}
    for e in _load():
        rid, ev = e.get("run_id"), e.get("event")
        if ev == "run_start" and e.get("ticket_id") is not None:
            runs[rid] = {"run_id": rid, "ticket_id": e["ticket_id"], "started_at": e.get("ts"),
                         "finished_at": None, "status": "running", "usage": None, "boss_report": None}
        elif rid in runs:
            if ev in ("run_end", "run_failed"):
                runs[rid].update(finished_at=e.get("ts"), usage=e.get("usage"),
                                 status="completed" if ev == "run_end" else "failed")
            elif ev == "agent_end" and e.get("depth") == 0:
                runs[rid]["boss_report"] = (e.get("data") or {}).get("output")
    latest: dict[int, dict[str, Any]] = {}
    for r in runs.values():  # file order is chronological, so later runs overwrite earlier ones
        latest[r["ticket_id"]] = r
    return latest
