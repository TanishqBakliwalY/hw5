"""Customer Service: drafts every outgoing message (customers, clubs, landlord). Drafts only, never sent."""

from ..models import AgentReport
from .base import AgentSpec

SPEC = AgentSpec(
    name="customer_service",
    title="Customer Service",
    description="Drafts replies to customers, student orgs and the landlord using only confirmed facts. Drafts are never sent.",
    prompt_file="customer_service.md",
    mcp_tools=frozenset({"get_shop_date", "get_ticket", "get_stock_and_price", "check_order_fill"}),
    output_type=AgentReport,
)
