"""Accounting: cash, vendor invoices, and payment requests that wait for human approval."""

from ..models import AgentReport
from .base import AgentSpec

SPEC = AgentSpec(
    name="accounting",
    title="Accounting",
    description="Tracks cash and invoices, checks affordability (incl. pending requests), and files payment requests for human approval.",
    prompt_file="accounting.md",
    mcp_tools=frozenset({
        "get_shop_date", "get_ticket", "get_invoice_status", "list_open_invoices",
        "get_lease_rent_status", "get_cash_position", "request_payment",
        "list_payment_requests", "evaluate_discount",
    }),
    output_type=AgentReport,
)
