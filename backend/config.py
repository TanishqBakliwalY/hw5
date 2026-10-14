"""Paths, model and run limits shared by the whole agent team."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Project .env first; fall back to the course-workspace .env one level up. Never logged or printed.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"
ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"
AUDIT_TRAIL = PROJECT_ROOT / "output" / "audit_trail.json"

# The only model the team may use. Not overridable by environment variables on purpose.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_TIMEOUT_SECONDS = 180  # per model call

# ---- Token / loop limits ----
# One team run (all agents and delegations for one task) shares a single usage budget.
TEAM_REQUEST_LIMIT = 60         # model round-trips across every agent in the run (a full 3-ticket run uses ~38)
TEAM_TOOL_CALLS_LIMIT = 80       # MCP + delegate tool executions across the run
TEAM_TOTAL_TOKENS_LIMIT = 250_000  # input + output tokens across the run
MAX_DELEGATION_DEPTH = 3         # boss(0) -> a(1) -> b(2) -> c(3); deeper hand-offs are refused
AGENT_OUTPUT_RETRIES = 2         # retries when an agent's structured output fails validation
AUDIT_TEXT_LIMIT = 4000          # max characters of any single text/result stored in the audit trail
