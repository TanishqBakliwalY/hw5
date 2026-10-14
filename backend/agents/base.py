"""Shared machinery for the five agents: building them, delegating between them, and
running each agent loop step by step with audit logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import RunUsage, UsageLimits

from .. import audit
from ..config import (
    AGENT_OUTPUT_RETRIES,
    MAX_DELEGATION_DEPTH,
    PROMPTS_DIR,
    TEAM_REQUEST_LIMIT,
    TEAM_TOOL_CALLS_LIMIT,
    TEAM_TOTAL_TOKENS_LIMIT,
)
from ..llm import get_model
from ..models import AgentName, TeamDeps

if TYPE_CHECKING:
    from pydantic_ai.toolsets import AbstractToolset

AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

TEAM_LIMITS = UsageLimits(
    request_limit=TEAM_REQUEST_LIMIT,
    tool_calls_limit=TEAM_TOOL_CALLS_LIMIT,
    total_tokens_limit=TEAM_TOTAL_TOKENS_LIMIT,
)


@dataclass(frozen=True)
class AgentSpec:
    """Everything that defines one role on the team."""

    name: AgentName
    title: str
    description: str  # one line, shown to other agents so they know whom to delegate to
    prompt_file: str
    mcp_tools: frozenset[str]
    output_type: type[BaseModel]

    def prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- delegation tool


async def delegate(
    ctx: RunContext[TeamDeps],
    to_agent: AgentName,
    task: str,
    reason: str,
    ticket_id: int | None = None,
) -> str:
    """Hand a piece of work to another agent on the team and get its report back.

    Args:
        to_agent: who should do it: boss, inventory, accounting, facilities or customer_service.
        task: a clear, self-contained instruction, including the ticket id and any facts
              (numbers, dates) the other agent will need so it does not repeat lookups.
        reason: one sentence on why this agent is the right owner.
        ticket_id: the ticket this work is for, if any.
    """
    deps = ctx.deps
    refusal = None
    if to_agent == deps.agent:
        refusal = "You cannot delegate to yourself; do the work directly."
    elif to_agent in deps.chain:
        refusal = (
            f"{to_agent} is already working higher up this delegation chain "
            f"({' -> '.join(deps.chain)}); return your findings instead of handing work back."
        )
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        refusal = f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; finish with what you have."
    if refusal:
        audit.record(deps, "delegation", "delegation_refused", {"to_agent": to_agent, "task": task, "why": refusal})
        return json.dumps({"delegation_refused": refusal})

    audit.record(
        deps, "delegation", "delegation_start",
        {"to_agent": to_agent, "task": task, "reason": reason, "ticket_id": ticket_id},
    )
    report = await deps.team.run_agent(
        to_agent, task, parent=deps, usage=ctx.usage, ticket_id=ticket_id or deps.ticket_id
    )
    audit.record(
        deps, "delegation", "delegation_result",
        {"to_agent": to_agent, "report": report.model_dump(mode="json")},
    )
    return report.model_dump_json()


# --------------------------------------------------------------------------- building agents


def build_agent(spec: AgentSpec, shop_tools: AbstractToolset[TeamDeps], roster: dict[str, AgentSpec]) -> Agent:
    """Create one PydanticAI agent: its prompt file, its MCP tool subset, and the delegate tool."""
    agent: Agent[TeamDeps, Any] = Agent(
        get_model(),
        name=spec.name,
        deps_type=TeamDeps,
        output_type=spec.output_type,
        instructions=spec.prompt(),
        toolsets=[shop_tools],
        tools=[delegate],
        retries=AGENT_OUTPUT_RETRIES,
    )

    @agent.instructions
    def run_context(ctx: RunContext[TeamDeps]) -> str:
        d = ctx.deps
        others = "\n".join(
            f"- `{s.name}` ({s.title}): {s.description}" for s in roster.values() if s.name != d.agent
        )
        chain = " -> ".join((*d.chain, d.agent))
        blocked = sorted(set(d.chain))
        lines = [
            "## This run",
            f"- You are `{d.agent}`. Delegation chain so far: {chain}.",
            f"- Delegation depth {d.depth} of max {MAX_DELEGATION_DEPTH}."
            + (" You cannot delegate further." if d.depth >= MAX_DELEGATION_DEPTH else ""),
        ]
        if blocked:
            lines.append(f"- Do not delegate back to: {', '.join(blocked)} (they are waiting on you).")
        if d.ticket_id is not None:
            lines.append(
                f"- Focus ticket: {d.ticket_id}. Work ONLY this ticket. Other tickets are out of scope for this run: "
                "you may read shared facts (cash, existing payment requests) for context, but do not delegate, "
                "file payment requests, draft messages, or change status for any other ticket."
            )
        lines += ["", "## Teammates you can delegate to (tool `delegate`)", others]
        return "\n".join(lines)

    return agent


# --------------------------------------------------------------------------- the agent loop


def _usage_dict(u: Any) -> dict[str, Any] | None:
    if u is None:
        return None
    keys = ("input_tokens", "output_tokens", "cache_read_tokens", "requests", "tool_calls")
    return {k: getattr(u, k) for k in keys if hasattr(u, k)}


def _describe_request(parts: list[Any]) -> list[dict[str, Any]]:
    out = []
    for p in parts:
        if isinstance(p, UserPromptPart):
            out.append({"type": "user_prompt", "content": p.content if isinstance(p.content, str) else str(p.content)})
        elif isinstance(p, ToolReturnPart):
            out.append({"type": "tool_return", "tool": p.tool_name, "tool_call_id": p.tool_call_id})
        elif isinstance(p, RetryPromptPart):
            out.append({"type": "retry", "tool": p.tool_name, "content": str(p.content)})
        else:
            out.append({"type": type(p).__name__})
    return out


def _describe_response(parts: list[Any]) -> list[dict[str, Any]]:
    out = []
    for p in parts:
        if isinstance(p, TextPart):
            out.append({"type": "text", "content": p.content})
        elif isinstance(p, ToolCallPart):
            out.append({"type": "tool_call", "tool": p.tool_name, "args": p.args_as_dict(), "tool_call_id": p.tool_call_id})
        elif isinstance(p, ThinkingPart):
            out.append({"type": "thinking", "chars": len(p.content or "")})
        else:
            out.append({"type": type(p).__name__})
    return out


async def run_agent_loop(agent: Agent, deps: TeamDeps, task: str, usage: RunUsage) -> BaseModel:
    """Run one agent to completion, logging every step of its loop to the audit trail.

    `usage` is shared across the whole team run, so TEAM_LIMITS cap the total cost of a
    task no matter how many agents and delegations it takes.
    """
    audit.record(deps, "agent", "agent_start", {"task": task})
    step = 0
    try:
        async with agent.iter(task, deps=deps, usage=usage, usage_limits=TEAM_LIMITS) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    step += 1
                    audit.record(
                        deps, "llm", "model_request",
                        {"step": step, "parts": _describe_request(node.request.parts)},
                    )
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    audit.record(
                        deps, "llm", "model_response",
                        {
                            "step": step,
                            "model_name": resp.model_name,
                            "finish_reason": resp.finish_reason,
                            "parts": _describe_response(resp.parts),
                        },
                        usage=_usage_dict(resp.usage),
                    )
            output = run.result.output
            if getattr(output, "agent", deps.agent) != deps.agent:  # the report is always signed by who ran
                output = output.model_copy(update={"agent": deps.agent})
            audit.record(
                deps, "agent", "agent_end",
                {"steps": step, "output": output.model_dump(mode="json")},
                usage=_usage_dict(run.usage),
            )
            return output
    except Exception as exc:
        audit.record(deps, "agent", "agent_error", {"steps": step, "error": repr(exc)}, usage=_usage_dict(usage))
        raise
