"""Inventory: stock levels, shortfalls, vendor choice and restock ETAs."""

from ..models import AgentReport
from .base import AgentSpec

SPEC = AgentSpec(
    name="inventory",
    title="Inventory Manager",
    description="Checks stock and shortfalls, picks the right vendor, and works out restock ETAs (knows vendor holds).",
    prompt_file="inventory.md",
    mcp_tools=frozenset({
        "get_shop_date", "get_ticket", "get_stock_and_price", "check_order_fill",
        "list_vendors", "get_vendor_eta", "get_invoice_status", "list_payment_requests",
    }),
    output_type=AgentReport,
)
