"""The single connection between the agents and the campus-customs MCP server.

All shop facts and every shop change go through this MCP toolset -- there is no
second tools layer. One stdio MCP server process is shared by the whole team, and
each agent sees only the subset of MCP tools its role needs (least privilege).
Every MCP call and its result is written to the audit trail (layer 'mcp').
"""

from __future__ import annotations

import sys
import time
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.toolsets import AbstractToolset

from . import audit
from .config import MCP_SERVER_SCRIPT, PROJECT_ROOT
from .models import TeamDeps


async def _audited_call(
    ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]
) -> Any:
    deps = ctx.deps
    audit.record(deps, "mcp", "tool_call", {"tool": name, "args": args, "tool_call_id": ctx.tool_call_id})
    started = time.perf_counter()
    try:
        result = await call_tool(name, args)
    except Exception as exc:  # recorded, then surfaced to the agent loop as usual
        audit.record(deps, "mcp", "tool_error", {"tool": name, "error": repr(exc)})
        raise
    audit.record(
        deps,
        "mcp",
        "tool_result",
        {
            "tool": name,
            "tool_call_id": ctx.tool_call_id,
            "ms": round((time.perf_counter() - started) * 1000),
            "result": result,
        },
    )
    return result


def build_shop_toolset() -> MCPToolset:
    """Launch mcp_server/server.py over stdio with this project's Python interpreter."""
    transport = StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        cwd=str(PROJECT_ROOT),
    )
    return MCPToolset(
        Client(transport),
        id="campus-customs",
        process_tool_call=_audited_call,
        max_retries=1,
    )


def tools_for_role(shop: MCPToolset, allowed: frozenset[str]) -> AbstractToolset[TeamDeps]:
    """Only expose the MCP tools a given agent role is allowed to call."""
    return shop.filtered(lambda _ctx, tool_def: tool_def.name in allowed)
