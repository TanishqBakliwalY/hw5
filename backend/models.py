"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .team import Team

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_on_human", "resolved"]
AuditLayer = Literal["run", "agent", "llm", "mcp", "delegation", "human"]


# --------------------------------------------------------------------------- agent outputs


class Fact(BaseModel):
    """A shop fact the agent relied on, with where it came from."""

    statement: str = Field(description="The fact in one short sentence, with exact numbers/dates.")
    source: str = Field(
        description="MCP tool that returned it (e.g. 'get_invoice_status') or 'delegation:<agent>'."
    )


class HumanAction(BaseModel):
    """Something only a human can do, surfaced for the dashboard."""

    kind: Literal["approve_payment", "approve_discount", "decision"]
    description: str
    ticket_id: int | None = None
    payment_request_id: int | None = Field(
        default=None, description="payment_requests.id returned by request_payment, if any."
    )


class DraftMessage(BaseModel):
    """An outgoing message drafted for human review. Never sent by the system."""

    recipient: str
    subject: str
    body: str
    ticket_id: int | None = None
    status: Literal["draft_not_sent"] = "draft_not_sent"


class AgentReport(BaseModel):
    """What a specialist agent (Inventory, Accounting, Facilities, Customer Service) hands back."""

    agent: AgentName
    ticket_ids: list[int] = Field(default_factory=list)
    summary: str = Field(description="2-4 sentences: what was checked, found and done.")
    facts: list[Fact] = Field(default_factory=list)
    actions_taken: list[str] = Field(
        default_factory=list, description="Changes made through MCP tools (e.g. payment request #1 created)."
    )
    human_actions_needed: list[HumanAction] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list, description="Anything blocked or unknown.")


class TicketOutcome(BaseModel):
    ticket_id: int
    ticket_type: str
    status: TicketStatus
    agents_involved: list[AgentName]
    summary: str
    human_actions_needed: list[HumanAction] = Field(default_factory=list)
    drafts: list[DraftMessage] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class BossReport(BaseModel):
    """The Boss's final report for a run."""

    shop_date: str = Field(description="desk.date_today used for this run.")
    tickets: list[TicketOutcome]
    cash_summary: str = Field(description="Cash, pending requests and available cash after this run.")
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- run state / deps


@dataclass
class RunState:
    """Shared by every agent in one team run."""

    run_id: str
    task: str
    seq: int = 0  # audit step counter across the whole run

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


@dataclass
class TeamDeps:
    """Per-agent dependencies passed to each PydanticAI run."""

    agent: AgentName
    run: RunState
    team: "Team"
    depth: int = 0
    chain: tuple[AgentName, ...] = field(default_factory=tuple)
    ticket_id: int | None = None


class AuditEvent(BaseModel):
    """One line in output/audit_trail.json."""

    ts: str
    run_id: str
    seq: int
    layer: AuditLayer
    event: str
    agent: AgentName | None = None
    depth: int | None = None
    chain: list[str] = Field(default_factory=list)
    ticket_id: int | None = None
    model: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] | None = None
