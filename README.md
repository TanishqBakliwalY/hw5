# Campus Customs — Multi-Agent Operations Team

AI Foundations for Managers · Homework 5

Campus Customs is a campus apparel shop on Chapel Street. Five **PydanticAI** agents (**Boss, Inventory, Accounting, Facilities, Customer Service**) work the shop's tickets, delegating to each other. All shop data comes through one **FastMCP** server over a SQLite working database. A **FastAPI** backend runs the team and exposes routes, and a **React** board lets a human watch the agents work and approve payments. Only a human approval moves money.

```
React board (frontend/, :5173) ──▶ FastAPI (backend/main.py, :8000) ──▶ agent team (backend/) ──▶ MCP server (mcp_server/server.py) ──▶ data/campus_customs_new.db
                                                                          gpt-6-luna via Portkey
```

## What's in the repo

```
hw5/
├── AI_prompts.md            log of the prompts used to build this, problem by problem
├── requirements.txt         Python dependencies
├── .env.example             copy to .env and add PORTKEY_API_KEY (the real .env is git-ignored)
├── .mcp.json                MCP server entry for Claude Code (vibe coder)
├── data/
│   ├── campus_customs.db        ORIGINAL database — never modified
│   └── campus_customs_new.db    WORKING copy — every agent read/write goes here
├── mcp_server/              FastMCP server (15 shop tools) + README
├── backend/                 FastAPI app (main.py), agent team, data types (models.py)
│   ├── agents/              boss / inventory / accounting / facilities / customer_service + shared agent loop
│   └── prompts/             one system prompt per agent
├── frontend/                React + Vite + TypeScript board
└── output/                  harness.md, mcp_smoke.json, desk_tickets.html, design.md,
                             resolved_tickets.json, resolved_board.html, audit_trail.json, github_url.txt
```

> The committed `campus_customs_new.db` holds the **end state of the graded run** (all three tickets resolved, checking **$160.00**), so it matches `output/desk_tickets.html` → Cash. **Reset it before your own run** (step 2).

## Requirements

- Python 3.11+ (built and tested with 3.14)
- Node.js 20+ and npm (tested with Node 24)
- A Portkey API key with access to `gpt-6-luna`

## 1. One-time setup

```bash
git clone <this repo>
cd <repo>

# Python environment
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

# your key (never commit .env)
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# then edit .env and set PORTKEY_API_KEY=...

# React board
cd frontend
npm install
cd ..
```

## 2. Get a clean working database

The original `data/campus_customs.db` is never changed. All work happens in `data/campus_customs_new.db`. To start fresh, copy the original over the working copy:

```bash
# macOS/Linux/Git Bash
cp data/campus_customs.db data/campus_customs_new.db
```
```powershell
# Windows PowerShell
Copy-Item data\campus_customs.db data\campus_customs_new.db -Force
```

Once the backend is running, you can do the same with `POST http://localhost:8000/api/reset` (or `python -m backend.run_team --reset`). After a reset, checking starts at **$3,400.00**, tickets 101/102/103 are open, and invoice 501 is unpaid.

## 3. Start the MCP server

The MCP server exposes the 15 shop tools (stock, vendors, invoices, leases, cash, payment requests, tickets) over `data/campus_customs_new.db`.

- **With the app you don't start it by hand.** Each team run launches `mcp_server/server.py` over stdio with the project's Python and shuts it down afterwards (`backend/mcp_link.py`).
- **To run it on its own** (for example, to inspect it):
  ```bash
  python mcp_server/server.py
  ```
- **To use it from Claude Code**, open the repo folder with the virtual environment active. `.mcp.json` registers the `campus-customs` server (`python mcp_server/server.py`); approve it when prompted.

## 4. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000, with interactive docs at http://localhost:8000/docs. Key routes:

| Route | What it does |
|---|---|
| `GET /api/tickets` | The three tickets with status (open / resolved), linked payments, latest run |
| `POST /api/tickets/{id}/run` | Run the agent team (Boss first) on one ticket |
| `GET /api/events` | Recent agent events: what each agent said and which tools it used |
| `GET /api/payments` | Payment requests the agents prepared |
| `POST /api/payments/{id}/approve` | A human approves a payment. **The only route that changes cash** |
| `POST /api/payments/{id}/deny` | A human denies a payment |
| `GET /api/cash` | Current checking balance from `cash_accounts` |
| `POST /api/reset` | Copy the original DB over the working copy |

On Windows, if `--reload` ever stops picking up edits, stop the server with Ctrl+C and start it again.

## 5. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

This opens http://localhost:5173, which calls the backend at http://localhost:8000 (the backend allows this origin via CORS). Type your name in **Approving as** in the header. Only a person can approve money.

## 6. Full three-ticket run

1. **Reset the working DB** (step 2, or `curl -X POST http://localhost:8000/api/reset`). Checking should read **$3,400.00**.
2. On the board, open **#ticket-101** → **Hand to the team**. Watch the nameplates and chat. When the run ends, an **Action needed** card asks to pay Bulldog Print Co **$840.00** (overdue invoice 501). Click **Approve & pay**. Checking drops to $2,560.00 and the ticket flips to **Resolved**.
3. Open **#ticket-102** → **Hand to the team** → approve the **$2,400.00** rent to Elm City Properties. Checking is now $160.00.
4. Open **#ticket-103** → **Hand to the team**. The Boss prices the 20-hoodie bulk order within policy, and no payment is needed (invoice 501 is already paid). The ticket resolves when the run ends.
5. Checking ends at **$3,400.00 − $840.00 − $2,400.00 = $160.00**, which equals `cash_accounts` in the working DB.

Command-line alternative (no board): `python -m backend.run_team --reset` works the whole queue. Payments still wait for a human approval through the API.

## Shop rules the system enforces

- Every payment needs **human approval**. Agents can only file `payment_requests`, and approval happens on the board.
- A payment is **rejected if cash is insufficient** (checked when the request is filed and again when it's approved).
- A vendor with **unpaid invoices cannot ship**.
- **No real emails or vendor messages.** Customer Service writes drafts only.
- "Today" is `desk.date_today` (2026-08-31), never the computer clock.
- Every agent uses **only `gpt-6-luna` via Portkey**, with limits per run of 60 model calls, 80 tool calls, 250k tokens, delegation depth 3, and a 180 s timeout per model call.
- Every agent step, tool call, delegation and human decision is **appended** to `output/audit_trail.json`.

More detail: `output/harness.md` (tables, tools, agents, routes, dashboard, safety), `mcp_server/README.md`, and `output/design.md` (board design).
