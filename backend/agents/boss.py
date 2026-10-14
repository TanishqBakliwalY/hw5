"""Boss: reads the ticket queue, routes work, approves discounts within policy, owns ticket status and the final report."""

from ..models import BossReport
from .base import AgentSpec

SPEC = AgentSpec(
    name="boss",
    title="Boss / Operations Lead",
    description="Triages tickets, routes and coordinates work, decides discounts within policy, sets ticket status, writes the final report.",
    prompt_file="boss.md",
    mcp_tools=frozenset({
        "get_shop_date", "list_open_tickets", "get_ticket", "update_ticket",
        "get_stock_and_price", "evaluate_discount", "get_cash_position", "list_payment_requests",
    }),
    output_type=BossReport,
)
