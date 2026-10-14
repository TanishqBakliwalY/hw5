"""Facilities: the shop space, its lease and rent timeline."""

from ..models import AgentReport
from .base import AgentSpec

SPEC = AgentSpec(
    name="facilities",
    title="Facilities",
    description="Owns the lease and rent timeline for the Chapel Street shop; hands rent payments to Accounting.",
    prompt_file="facilities.md",
    mcp_tools=frozenset({
        "get_shop_date", "get_ticket", "get_lease_rent_status",
        "get_cash_position", "list_payment_requests",
    }),
    output_type=AgentReport,
)
