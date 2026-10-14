"""The Campus Customs team: five agents wired to one MCP server and to each other.

    async with Team() as team:
        report = await team.run_task("Work every open ticket.")

Any agent can delegate to any other (full connectivity); loops are prevented by
refusing hand-offs back up the current chain and by MAX_DELEGATION_DEPTH.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from . import audit
from .agents import ROSTER
from .agents.base import build_agent, run_agent_loop
from .config import MAX_DELEGATION_DEPTH, MODEL_NAME, TEAM_REQUEST_LIMIT, TEAM_TOOL_CALLS_LIMIT, TEAM_TOTAL_TOKENS_LIMIT, WORKING_DB
from .mcp_link import build_shop_toolset, tools_for_role
from .models import AgentName, RunState, TeamDeps


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def ticket_task(ticket_id: int) -> str:
    """The Boss's instruction for working a single ticket (used by the CLI and the API)."""
    return f"Work ticket {ticket_id} end to end following your playbook and return your report."


class Team:
    def __init__(self) -> None:
        if not WORKING_DB.exists():
            raise FileNotFoundError(f"{WORKING_DB} is missing. Run with --reset to copy the original database.")
        self.shop = build_shop_toolset()
        self.agents: dict[AgentName, Agent] = {
            name: build_agent(spec, tools_for_role(self.shop, spec.mcp_tools), ROSTER)
            for name, spec in ROSTER.items()
        }

    async def __aenter__(self) -> "Team":
        await self.shop.__aenter__()  # one MCP server process for the whole team
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.shop.__aexit__(*exc)

    async def run_agent(
        self,
        name: AgentName,
        task: str,
        *,
        parent: TeamDeps,
        usage: RunUsage,
        ticket_id: int | None = None,
    ) -> BaseModel:
        """Run `name` as a sub-agent of `parent` (used by the delegate tool)."""
        deps = TeamDeps(
            agent=name,
            run=parent.run,
            team=self,
            depth=parent.depth + 1,
            chain=(*parent.chain, parent.agent),
            ticket_id=ticket_id,
        )
        return await run_agent_loop(self.agents[name], deps, task, usage)

    async def run_task(
        self,
        task: str,
        *,
        start_agent: AgentName = "boss",
        ticket_id: int | None = None,
        run_id: str | None = None,
    ) -> BaseModel:
        """Start a new team run (new run_id, fresh shared usage budget) at `start_agent`."""
        state = RunState(run_id=run_id or new_run_id(), task=task)
        deps = TeamDeps(agent=start_agent, run=state, team=self, ticket_id=ticket_id)
        usage = RunUsage()
        audit.record(
            deps, "run", "run_start",
            {
                "task": task,
                "start_agent": start_agent,
                "model": MODEL_NAME,
                "database": WORKING_DB.name,
                "limits": {
                    "requests": TEAM_REQUEST_LIMIT,
                    "tool_calls": TEAM_TOOL_CALLS_LIMIT,
                    "total_tokens": TEAM_TOTAL_TOKENS_LIMIT,
                    "max_delegation_depth": MAX_DELEGATION_DEPTH,
                },
            },
            agent_level=False,
        )
        try:
            output = await run_agent_loop(self.agents[start_agent], deps, task, usage)
        except Exception as exc:
            audit.record(deps, "run", "run_failed", {"error": repr(exc)},
                         usage={"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                                "requests": usage.requests, "tool_calls": usage.tool_calls},
                         agent_level=False)
            raise
        audit.record(
            deps, "run", "run_end", {"start_agent": start_agent},
            usage={"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                   "requests": usage.requests, "tool_calls": usage.tool_calls},
            agent_level=False,
        )
        return output
