"""The five Campus Customs agents. ROSTER maps each role name to its spec."""

from . import accounting, boss, customer_service, facilities, inventory
from .base import AgentSpec

ROSTER: dict[str, AgentSpec] = {
    m.SPEC.name: m.SPEC for m in (boss, inventory, accounting, facilities, customer_service)
}
