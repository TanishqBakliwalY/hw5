# Campus Customs — Agent Harness

This harness is the reference for the Campus Customs multi-agent operations team: five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) that work the shop's tickets through one MCP server, plus a FastAPI backend and a React desk where a human watches the agents and approves money.

**Contents:** [Model and data](#model-and-data) · [Tables](#tables) · [Open tickets](#open-tickets-and-how-they-connect) · [MCP tools](#all-mcp-tools-and-the-tables-they-use) · [Agents](#agent-team-problem-5--pydanticai-backend) · [Audit trail](#audit-trail--outputaudit_trailjson) · [Safety](#safety) · [API routes](#backend-api-routes-problem-7--backendmainpy) · [Dashboard](#dashboard-problem-8--frontend) · [Full run results](#full-run-results-problem-9) · [Running it](#running-it)

```
 React desk (frontend/, :5173) --HTTP--> FastAPI (backend/main.py, :8000) --> shop_db.py (human-only: approve / deny / reset / resolve)
                                               |
                                               +-- runs --> Team (backend/team.py): Boss <-> Inventory <-> Accounting <-> Facilities <-> Customer Service
                                                              | gpt-6-luna via Portkey            | every shop fact / change
                                                              v                                   v
                                               output/audit_trail.json (append-only)     MCP server (mcp_server/server.py, stdio)
                                                                                                  |
                                                                                                  v
                                                                                  data/campus_customs_new.db (working copy)
```

## Model and data

- **LLM:** `gpt-6-luna` through Portkey, authenticated with `PORTKEY_API_KEY` from `.env`. No other model is used.
- **Original database:** `data/campus_customs.db`. Read-only reference that is never modified.
- **Working copy:** `data/campus_customs_new.db`. Every agent read and write goes here. Before a full run, reset it by copying the original over it again.
- **"Today":** always read from `desk.date_today` (currently `2026-08-31`), never the system clock.

## Tables

### `desk`
| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | Simulated current date (`2026-08-31`) |
| `notes` | TEXT | Free-form desk notes (currently empty) |

**Why it matters:** This is the shop's clock. Every overdue or due-soon decision (invoices, rent) compares against `date_today`.

### `tickets`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Ticket number |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override` |
| `requester` | TEXT | Who raised the ticket |
| `subject` | TEXT | Short title |
| `sku`, `size`, `qty` | TEXT, TEXT, INTEGER | Product line the ticket is about (if any) |
| `lease_id` | INTEGER FK → `leases.id` | Linked lease (rent tickets) |
| `invoice_id` | INTEGER FK → `invoices.id` | Linked vendor invoice |
| `status` | TEXT | `open` for all three now |
| `notes` | TEXT | Details from the requester |
| `created_at` | TEXT | ISO timestamp |

**Why it matters:** This is the work queue. The Boss reads open tickets and routes each one to the right agent. The foreign keys show which other tables each ticket touches.

### `inventory`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT (PK part) | Product code |
| `name` | TEXT | Product name |
| `size` | TEXT (PK part) | S/M/L/XL or `OS` (one size) |
| `qty` | INTEGER | Units on hand |
| `location` | TEXT | Aisle |

**Why it matters:** The Inventory agent uses it to check whether an order can be filled from stock or needs a reprint or restock. Two lines are already out of stock: `CC-TEE-WHITE` size S and `CC-MUG-CREST`.

### `pricing`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | Product code |
| `unit_cost` | REAL | What the shop pays |
| `list_price` | REAL | Normal selling price |

**Why it matters:** Accounting and the Boss use it to judge discounts. Any price override must stay above `unit_cost` to protect the margin.

### `vendors`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Vendor ID |
| `name` | TEXT | Bulldog Print Co, Elm City Gifts, QuickShip CT |
| `specialty` | TEXT | Apparel reprint / mugs and small goods / local courier |
| `lead_days` | INTEGER | Days to deliver (5 / 3 / 1) |

**Why it matters:** The Inventory agent picks a vendor for restocks and uses `lead_days` to give delivery dates. Vendors cannot ship while they have unpaid invoices. Vendor contact is drafted only and never actually sent.

### `invoices`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Invoice number |
| `vendor_id` | INTEGER FK → `vendors.id` | Who billed us |
| `amount` | REAL | Amount owed |
| `due_date` | TEXT | Compare with `desk.date_today` for overdue |
| `status` | TEXT | `open` = unpaid |
| `description` | TEXT | What it was for |

**Why it matters:** Accounting tracks what is owed and what is overdue. An open invoice blocks that vendor from shipping until it is paid.

### `cash_accounts`
| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | Account name (`checking`) |
| `balance` | REAL | Available cash (`$3,400.00`) |
| `date` | TEXT | Balance as-of date |

**Why it matters:** Accounting must check this before any payment. A payment is rejected if the balance is not enough.

### `payments`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Payment ID |
| `kind` | TEXT | e.g. invoice or rent |
| `ref_id` | INTEGER | ID of the invoice or lease being paid |
| `amount` | REAL | Amount paid |
| `account` | TEXT | Cash account it came from |
| `paid_at` | TEXT | Date paid |
| `approved_by` | TEXT | Human approver (required) |

**Why it matters:** This is the audit trail of money out (empty now). A row is written only after a human approves on the dashboard, so `approved_by` must never be an agent.

### `leases`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Lease ID |
| `space_name` | TEXT | Chapel Street shop |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | `$2,400.00` |
| `next_due` | TEXT | `2026-09-02` |
| `notes` | TEXT | — |

**Why it matters:** The Facilities agent handles rent and lease questions. It schedules the rent payment request, which then goes through Accounting and human approval.

### Tables the system adds (working copy only)

These are created on demand in `data/campus_customs_new.db` and vanish on reset. The original database never gets them.

#### `payment_requests` (written by the MCP tool `request_payment`; decided through the human API)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Request number shown on the Approve card |
| `kind` / `ref_id` | TEXT / INTEGER | `invoice` → `invoices.id`, `rent` → `leases.id` |
| `payee`, `amount` | TEXT, REAL | Read from the DB, never typed by an agent |
| `reason`, `requested_by`, `requested_on` | TEXT | The agent's reason, which agent filed it, and `desk.date_today` |
| `status` | TEXT | `pending_approval` → `approved` / `denied` / `rejected_insufficient_cash` |
| `decided_by`, `decided_at` | TEXT | Human name and shop date of the decision |
| `created_at` | TEXT | Wall-clock UTC for audit |

**Why it matters:** This is the boundary between agents and money. Agents can only add rows here; only a human decision on the board turns a row into a `payments` row.

#### `ticket_events` (written by `update_ticket` and by the desk)
`id, ticket_id, actor, old_status, new_status, note, shop_date, created_at`. This is the status history of every ticket. `actor` is the agent (`boss`) or `desk` when the backend resolves or reopens a ticket.

#### `ticket_payment_links` (written by the backend after each run)
`ticket_id, request_id, run_id`. This records which payment requests a ticket's run filed or depends on. A ticket resolves only when every linked request has been decided.

## Open tickets and how they connect

| Ticket | Type | Linked tables | What the data shows | Likely agents |
|---|---|---|---|---|
| **101** — Tauhid Zaman, 1× Bulldog tee size S | `customer_order` | `inventory`, `invoices` (501) → `vendors` (1), `cash_accounts`, `payments` | `CC-TEE-WHITE` S has **0** in stock. Invoice 501 (Bulldog Print Co, $840, "Rush reprint CC-TEE-WHITE S") was due 2026-08-28 and is still `open`, so it is **overdue** on 2026-08-31. Bulldog cannot ship the reprint until it is paid. After payment, lead time is 5 days. | Inventory → Accounting (pay 501, human approval) → Customer Service (draft reply with ETA) |
| **102** — Elm City Properties, rent due | `rent_notice` | `leases` (1), `cash_accounts`, `payments` | $2,400 rent for Chapel Street shop is due 2026-09-02. That is in 2 days, so it is due soon but not overdue. | Facilities → Accounting (payment request, human approval) |
| **103** — Yale AI Club, 20 hoodies size M, bulk discount | `price_override` | `inventory`, `pricing`, `vendors` | `CC-HOOD-NAVY` M has only **8** in stock, so the order is 12 short. List price is $58 and unit cost is $22, so any discount must stay above $22. Restocking would come from Bulldog Print Co, which is blocked until invoice 501 is paid. | Boss (approves discount) + Inventory (stock/reprint) + Accounting (margin) → Customer Service (draft reply) |

### Cross-ticket constraint: cash
Checking has **$3,400**. Paying invoice 501 ($840) and rent ($2,400) together comes to **$3,240**, leaving only **$160**. Accounting must re-check the balance before each payment. Any later payment that exceeds the remaining cash must be rejected.

## MCP tools — the first three (Problem 3)

Every agent uses these FastMCP tools. They only read from `data/campus_customs_new.db` and return an `error` instead of guessing when a record is missing. The full list of tools, including those added in Problem 5, is in [All MCP tools and the tables they use](#all-mcp-tools-and-the-tables-they-use).

### 1. `get_stock_and_price(sku, size)`
- **Unlocks:** Ticket **101** and ticket **103**.
- **Why for 101:** Tauhid wants one `CC-TEE-WHITE` in size S. This tool returns `qty_on_hand = 0` for that exact line, which shows the order cannot be filled from the shelf and needs the Bulldog reprint.
- **Why for 103:** Yale AI Club wants 20 `CC-HOOD-NAVY` in size M. This tool returns the 8 on hand (12 short), plus `unit_cost = $22` and `list_price = $58`. The Boss needs both numbers to set a bulk discount that stays above cost.

### 2. `get_invoice_status(invoice_id)`
- **Unlocks:** Ticket **101** (and the restock half of 103).
- **Why for 101:** Ticket 101 links to `invoice_id = 501`. This tool shows that the $840 Bulldog Print Co reprint invoice is 3 days overdue on `desk.date_today`, that `vendor_can_ship = false`, and that Bulldog's lead time is 5 days. Those three facts tell Accounting to request approval to pay 501 and tell Customer Service what delivery date to quote.

### 3. `get_lease_rent_status(lease_id)`
- **Unlocks:** Ticket **102**.
- **Why for 102:** Ticket 102 links to `lease_id = 1`. This tool returns the $2,400 Chapel Street rent due 2026-09-02 (2 days from `desk.date_today`, not overdue) next to the $3,400 checking balance with `cash_covers_rent = true`. That gives Facilities and Accounting everything needed to raise a rent payment request for human approval.

---

## Agent team (Problem 5) — PydanticAI, `backend/`

All five agents use **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY` from `.env`), via the OpenAI **Responses API**. Chat Completions rejects function tools with reasoning for this model. Each agent's prompt lives in `backend/prompts/<agent>.md`. Data types are in `backend/models.py`.

| Agent | Code / prompt | Job | MCP tools it may call | Output |
|---|---|---|---|---|
| **Boss** | `agents/boss.py`, `prompts/boss.md` | Reads the queue, routes work by ticket type, decides discounts within policy (≤20% off list and ≥40% margin, never at/below cost), is the only agent that sets ticket status, writes the final report | `get_shop_date`, `list_open_tickets`, `get_ticket`, `update_ticket`, `get_stock_and_price`, `evaluate_discount`, `get_cash_position`, `list_payment_requests` | `BossReport` |
| **Inventory** | `agents/inventory.py`, `prompts/inventory.md` | Shortfall math (fill now vs short), picks vendor by specialty, ETA = `desk.date_today` + `lead_days`, flags vendor holds | `get_shop_date`, `get_ticket`, `get_stock_and_price`, `check_order_fill`, `list_vendors`, `get_vendor_eta`, `get_invoice_status`, `list_payment_requests` | `AgentReport` |
| **Accounting** | `agents/accounting.py`, `prompts/accounting.md` | The only agent that can file payment requests (pending human approval); checks available cash, including requests already pending | `get_shop_date`, `get_ticket`, `get_invoice_status`, `list_open_invoices`, `get_lease_rent_status`, `get_cash_position`, `request_payment`, `list_payment_requests`, `evaluate_discount` | `AgentReport` |
| **Facilities** | `agents/facilities.py`, `prompts/facilities.md` | Rent timeline for the lease from `desk.date_today`; hands the rent payment to Accounting | `get_shop_date`, `get_ticket`, `get_lease_rent_status`, `get_cash_position`, `list_payment_requests` | `AgentReport` |
| **Customer Service** | `agents/customer_service.py`, `prompts/customer_service.md` | Drafts every outgoing message (brand voice, only confirmed facts, privacy rules). Drafts are `draft_not_sent` | `get_shop_date`, `get_ticket`, `get_stock_and_price`, `check_order_fill` | `AgentReport` with `drafts` |

**Delegation (full connectivity):** every agent has a `delegate(to_agent, task, reason, ticket_id)` tool that can call any other agent (`agents/base.py`). It is blocked from calling itself, from calling an agent already waiting higher up the chain (prevents loops), and from going deeper than `MAX_DELEGATION_DEPTH = 3`. Each agent's instructions also list its teammates and the current chain.

**Scope:** a run started for one ticket (API / board) tells the Boss to work **only that ticket**. The run-wide instructions repeat it ("Work ONLY this ticket"), so other tickets get their own runs.

**Agent loop:** `run_agent_loop` drives each agent with `Agent.iter(...)`, one model request → tool calls → model request … until the structured output validates. The whole run (Boss plus every delegation) shares a single `RunUsage`, so the limits below cap the entire task.

**One tools layer:** agents have no database access of their own. Shop facts and shop changes go only through the `campus-customs` MCP server (`backend/mcp_link.py` launches `mcp_server/server.py` over stdio once per run). Each agent sees only its subset of tools.

**Run it:** `.venv/Scripts/python.exe -m backend.run_team --reset` (reset working DB, work all open tickets), `--ticket 102`, or `--agent inventory --task "..."`.

## All MCP tools and the tables they use

R = read, W = write. All tools use `data/campus_customs_new.db` only. `payment_requests` and `ticket_events` are agent tables created in the working copy by the server.

| # | Tool | Tables | R/W | Used by | Tickets |
|---|---|---|---|---|---|
| 1 | `get_shop_date` | `desk` | R | all | all |
| 2 | `list_open_tickets` | `tickets`, `desk` | R | Boss | all |
| 3 | `get_ticket` | `tickets`, `ticket_events`, `desk` | R | all | all |
| 4 | `update_ticket` | `tickets`, `ticket_events`, `desk` | **W** | Boss | all |
| 5 | `get_stock_and_price` | `inventory`, `pricing` | R | Boss, Inventory, Customer Service | 101, 103 |
| 6 | `check_order_fill` | `inventory` | R | Inventory, Customer Service | 101, 103 |
| 7 | `evaluate_discount` | `pricing` | R | Boss, Accounting | 103 |
| 8 | `list_vendors` | `vendors`, `invoices` | R | Inventory | 101, 103 |
| 9 | `get_vendor_eta` | `vendors`, `invoices`, `desk` | R | Inventory | 101, 103 |
| 10 | `get_invoice_status` | `invoices`, `vendors`, `desk` | R | Inventory, Accounting | 101 |
| 11 | `list_open_invoices` | `invoices`, `vendors`, `desk` | R | Accounting | 101 |
| 12 | `get_lease_rent_status` | `leases`, `cash_accounts`, `desk` | R | Accounting, Facilities | 102 |
| 13 | `get_cash_position` | `cash_accounts`, `payment_requests`, `desk` | R | Boss, Accounting, Facilities | 101, 102 |
| 14 | `request_payment` | `invoices`, `vendors`, `leases`, `cash_accounts`, `payment_requests`, `desk` | **W** (`payment_requests` only) | Accounting | 101, 102 |
| 15 | `list_payment_requests` | `payment_requests` | R | Boss, Inventory, Accounting, Facilities | 101, 102, 103 |

No tool writes to `payments`, `cash_accounts`, `invoices`, `inventory`, `pricing`, `vendors` or `leases`. Paying, changing stock and changing prices stay with the human.

## Audit trail — `output/audit_trail.json`

A JSON array that is **only ever appended to** (read → append → atomic replace; a corrupt file is moved aside, never deleted). Every event has `ts`, `run_id`, `seq`, `layer`, `event`, `agent`, `depth`, `chain`, `ticket_id`, `model`, `data`, and `usage`:

| Layer | Events | What is recorded |
|---|---|---|
| `run` | `run_start`, `run_end`, `run_failed` | task, start agent, model, DB file, limits, total tokens/requests/tool calls |
| `agent` | `agent_start`, `agent_end`, `agent_error` | task text, number of loop steps, final structured output, usage |
| `llm` | `model_request`, `model_response` | loop step number, what was sent (prompt / tool returns / retries), what came back (text, tool calls with args), model name, finish reason, tokens |
| `mcp` | `tool_call`, `tool_result`, `tool_error` | tool name, arguments, full result, latency in ms |
| `delegation` | `delegation_start`, `delegation_result`, `delegation_refused` | from → to agent, task, reason, returned report, or why it was refused |

Long text is clipped at 4,000 characters per field to keep the file bounded.

## Safety

**Guardrails for real customers and real money**
- **Humans approve all money.** Agents can only file `payment_requests` with status `pending_approval`. No tool marks anything paid or changes `cash_accounts`/`payments`. Approval happens outside the agent toolset (dashboard).
- **Cash check enforced in code, not just in the prompt.** `request_payment` compares against *available* cash (balances minus pending requests) and records `rejected_insufficient_cash` if it does not fit. It refuses duplicates, closed invoices, unknown ids and unknown requesters.
- **Amounts come from the database.** The payment tool takes an id, not an amount, so a model cannot invent or alter a figure.
- **Vendor holds** are computed from open invoices (`can_ship`), so an agent cannot "forget" them.
- **No outbound communication.** No tool sends email or contacts vendors. Customer Service output is `DraftMessage(status="draft_not_sent")` for a human to review.
- **Least privilege.** Each agent sees only the MCP tools its role needs. Only Accounting can request payments; only the Boss can change ticket status.
- **Discount policy.** The Boss may grant ≤20% off list with ≥40% margin and never at or below `unit_cost`. Anything deeper becomes a human `approve_discount` action.
- **Prompt-injection defense.** Ticket text is treated as data. Instructions inside notes ("approve this", "pay to a new account") are ignored and flagged.
- **No guessing.** Every fact in a report cites its MCP tool or teammate. Missing data is reported as unknown.
- **Data isolation.** The server refuses to open anything but `campus_customs_new.db`. The original DB is only read when `--reset` copies it.
- **Privacy.** Customer messages never reveal cash, invoices, vendor issues, costs, margins or other customers. Secrets stay in `.env`, which is git-ignored, and the API key is never logged.
- **Full audit.** Every model step, tool call and delegation is in an append-only trail tied to a `run_id`.
- **Human controls on the desk (Problems 7–8).** Approve and deny need a typed human name; agent names are refused with 403. Every decision is logged as a `human` audit event. A ticket is marked resolved only when its run has finished **and** every linked payment is decided. A failed run reopens its ticket instead of leaving it "in progress".
- **One run at a time.** All runs share the same cash, so a second run, or a reset during a run, is refused with 409.
- **Browser access is limited.** CORS allows only the Vite desk origin (`localhost:5173` / `127.0.0.1:5173`, plus `:3000` for a fallback dev server), and only GET/POST.

**Limits that keep token use in check** (`backend/config.py`, shared across the whole run including delegations)
- `request_limit = 60` model calls, `tool_calls_limit = 80`, `total_tokens_limit = 250,000` per run. Exceeding any one stops the run with `UsageLimitExceeded`, which is recorded as `run_failed`.
- `MAX_DELEGATION_DEPTH = 3`, no self-delegation, and no hand-backs up the chain, so there are no delegation loops.
- `AGENT_OUTPUT_RETRIES = 2` for structured-output validation.
- Measured on the Problem 9 board run: ticket 101 used 16 model calls / 19 tool calls / 53,129 tokens, ticket 102 used 13 model calls / 12 tool calls / 40,070 tokens, ticket 103 used 15 model calls / 15 tool calls / 50,848 tokens. Every run stayed well under every limit.
- `MODEL_TIMEOUT_SECONDS = 180` per model call (2 retries): a hung gateway call fails the run, and the ticket is reopened, instead of stalling for minutes. This was added after a 41-minute hang in testing.
- Prompts enforce token discipline: one lookup per fact, reuse facts handed over by teammates, short structured hand-offs.
- Measured: a full three-ticket run used **38 model requests, 52 tool calls, about 136k tokens** (124.7k in / 11.6k out). An earlier draft of the prompts re-verified facts and hit the tool-call cap at 60, so the cap did its job; the prompts were then tightened.

## Backend API routes (Problem 7) — `backend/main.py`

Start it from `backend/` with `uvicorn main:app --reload --port 8000`, which serves the API at `http://localhost:8000` (interactive docs at `/docs`). CORS is open to the React dev server on ports 5173 and 3000.

- `GET /api/health` — liveness check: model, working DB file, and the run in progress (if any).
- `GET /api/tickets` — every ticket with its status and `state` (`open` or `resolved`), its linked payment requests and pending-approval count, its latest team run (from the audit trail), and whether it is running now.
- `POST /api/tickets/{ticket_id}/resolve` (body `{"resolved_by", "note"}`) — a human closes a ticket by hand. Normally a ticket resolves itself once its run has finished and every payment request linked to it is approved, denied or rejected.
- `POST /api/tickets/{ticket_id}/run` — runs the agent team (Boss first) on that one ticket in the background and returns a `run_id`; add `?wait=true` to block and get the Boss's report. Only one run at a time (409 otherwise).
- `GET /api/runs` — runs started since the server came up, with status (`running` / `completed` / `failed`).
- `GET /api/runs/{run_id}` — one run's status and, when finished, the Boss's final report (ticket outcomes, drafts, human actions).
- `GET /api/events?after=&run_id=&ticket_id=&agent=&limit=` — recent events from `output/audit_trail.json`: what each agent said, which tools it called, and delegations, plus a per-agent rollup. Pass `next_after` back as `after` to fetch only new events on each refresh.
- `GET /api/payments?status=` — payment requests the agents prepared (e.g. `?status=pending_approval`).
- `POST /api/payments/{request_id}/approve` (body `{"approved_by": "<human name>"}`) — **the only route that changes cash**. It deducts from checking, writes a `payments` row, marks the request `approved`, and either marks the invoice `paid` (which lifts the vendor hold) or moves the lease's `next_due` forward a month. It is rejected (`rejected_insufficient_cash`, 409) if the balance is too low, and refuses agent names (403) and requests that are not pending (409).
- `POST /api/payments/{request_id}/deny` (body `{"decided_by", "reason"}`) — a human declines a prepared payment; no money moves.
- `GET /api/cash` — current checking balance from `cash_accounts`, plus pending requests, available-after-pending, and payments made.
- `POST /api/reset` — copies `data/campus_customs.db` over the working copy for a fresh run (refused while a run is in progress). The audit trail is kept.

Every approve, deny, reset and manual resolve is also appended to the audit trail as a `human`-layer event.

**Resolution rule (Problem 8):** when a run ends, the backend links the payment requests the run filed (or listed as human actions) to the ticket (`ticket_payment_links`) and calls `settle_ticket`. The ticket stays `waiting_on_human` while any linked request is pending, and flips to `resolved` (actor `desk`, logged in `ticket_events`) once every one has been decided. Approving or denying a request re-settles every ticket linked to it.

## Dashboard (Problem 8) — `frontend/`

React + Vite + TypeScript. `npm run dev` opens `http://localhost:5173`, which calls the backend at `http://localhost:8000` (`VITE_API_BASE` overrides that). The full design rationale is in `output/design.md`.

| Area | What it shows / does | API it uses |
|---|---|---|
| **Morning briefing** (header) | Greeting, the shop's date from `desk.date_today`, open tickets, $ waiting on you, checking balance, resolved count, the "Approving as" name, backend online dot | `/api/tickets`, `/api/cash` |
| **Desk nameplates** | One plate per agent: *at desk / thinking / using a tool / waiting on X / done*. The active agent glows | `/api/events` |
| **Ticket channels** (left) | `#ticket-101…103` with status pill (Open / Team working / Needs you / Resolved), amber badge for pending payments, ✓ when resolved | `/api/tickets` |
| **Channel** (center) | Live chat of the run: hand-offs (`@Agent` + why), tool chips that spin then tick with ms, reports with facts and sources, the Boss wrap-up with drafts (*never sent*), a shift report of who did what, docked **Approve & pay / Deny** cards, a RESOLVED stamp with confetti | `/api/events`, `POST /api/tickets/{id}/run`, `POST /api/payments/{id}/approve`, `…/deny` |
| **Cash card** (right) | Checking balance that rolls down on payment, a sparkline, a ledger of payments / pending / rejected, "left if you approve all" | `/api/cash`, `/api/payments` |
| **Plan vs actual** tab | The Problem 6 plan beside the live run: first call, hand-offs ✓/✗, unplanned hand-offs, planned vs extra tools | `/api/events` |
| **Run meter** tab | Run clock and bars for model calls / tool calls / tokens against the 60 / 80 / 250k limits | `/api/events`, `/api/health` |
| **Approval alerts** | Chime, toast, and the tab title `(1) Needs you` when an agent files a payment request | `/api/payments` |

Polling: shop state every 5 s (1.5 s while a run is live), and run events every 1.2 s, fetching only new events (`?after=`). `?ticket=101` in the URL opens that channel directly.

## Full run results (Problem 9)

The working DB was reset and all three tickets were run from the board, in order. A human (Tanishq Bakliwal) approved each payment on the board. Details are in `output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`, and the screenshots in `output/resolved_board.html`.

| Ticket | Run | Boss called first | Hand-offs | Payment approved | Checking after | Final |
|---|---|---|---|---|---|---|
| 101 tee | `e3525dc66a03` | Inventory ✓ | Boss→Inventory, Inventory→Accounting, Boss→Customer Service (3/3 planned) | #1 $840.00 → Bulldog Print Co (invoice 501) | $2,560.00 | resolved |
| 102 rent | `4232ceb2fffc` | Facilities ✓ | Boss→Facilities, Facilities→Accounting (2/2 planned; optional landlord draft skipped) | #2 $2,400.00 → Elm City Properties (lease 1) | $160.00 | resolved |
| 103 hoodies | `6d8d3685bb5e` | Inventory ✓ | Boss→Inventory, Boss→Customer Service (2/2 planned) | none: Boss approved $46.40 × 20 (20% off, 52.59% margin) within its authority; invoice 501 was already paid | $160.00 | resolved |

**Cash:** $3,400.00 start − $840.00 − $2,400.00 = **$160.00**, which equals `cash_accounts.balance` in the working DB. The `payments` table holds 2 rows totalling $3,240.00, both approved by a human.

## Running it

```bash
# backend (from backend/)
uvicorn main:app --reload --port 8000
# desk (from frontend/)
npm run dev
# optional: whole queue from the command line, fresh DB
python -m backend.run_team --reset
```

Use `POST /api/reset` (or `--reset`) before a full run. The audit trail is never reset.
