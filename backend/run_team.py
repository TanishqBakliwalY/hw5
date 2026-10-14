"""Run the Campus Customs team from the command line.

    .venv/Scripts/python.exe -m backend.run_team --reset              # full run: fresh working DB, all open tickets
    .venv/Scripts/python.exe -m backend.run_team --ticket 102         # one ticket
    .venv/Scripts/python.exe -m backend.run_team --agent inventory --task "Is CC-TEE-WHITE size S in stock?"

--reset copies data/campus_customs.db over data/campus_customs_new.db. The original is only read.
The audit trail (output/audit_trail.json) is appended to and never reset.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys

from .agents.base import AGENT_NAMES
from .config import ORIGINAL_DB, WORKING_DB
from .team import Team, ticket_task

FULL_RUN_TASK = (
    "Work every open ticket in the queue end to end following your playbook. "
    "Delegate to the right teammates, get payment requests filed for human approval where needed, "
    "get customer-facing replies drafted, set each ticket's status, and return your final report."
)


def reset_working_db() -> None:
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}.", file=sys.stderr)


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reset", action="store_true", help="copy the original DB over the working copy first")
    p.add_argument("--ticket", type=int, help="work only this ticket id")
    p.add_argument("--agent", choices=AGENT_NAMES, default="boss", help="agent to start with (default boss)")
    p.add_argument("--task", help="custom task text instead of the default")
    args = p.parse_args()

    if args.reset:
        reset_working_db()

    if args.task:
        task = args.task
    elif args.ticket is not None:
        task = ticket_task(args.ticket)
    else:
        task = FULL_RUN_TASK

    async with Team() as team:
        report = await team.run_task(task, start_agent=args.agent, ticket_id=args.ticket)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
