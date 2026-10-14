# Campus Customs MCP Server

This is a [FastMCP](https://gofastmcp.com) server. It is the **only** tools layer for the five Campus Customs agents (Boss, Inventory, Accounting, Facilities, Customer Service). Every shop fact an agent uses, and every change an agent makes, goes through these tools; agents never open the database themselves. The vibe coder (Claude Code) connects to it through the project's `.mcp.json`. The PydanticAI backend launches it over stdio (`backend/mcp_link.py`).

## Database

- Uses **`data/campus_customs_new.db`**, the working copy. The server refuses to open any other file.
- Never touches the original `data/campus_customs.db`. To reset, copy the original over the working copy (`python -m backend.run_team --reset`).
- "Today" is always `desk.date_today`, not the computer's clock.
- Tools return only what is in the database. If a record does not exist, they return an `error` instead of guessing.
- The server creates two agent tables in the working copy if they are missing: `payment_requests` (payments waiting for human approval) and `ticket_events` (ticket status history).

## Tools (15)

| Tool | Inputs | Tables | R/W | Returns / does |
|---|---|---|---|---|
| `get_shop_date` | — | `desk` | R | `date_today` and desk notes |
| `list_open_tickets` | — | `tickets` | R | Every ticket not yet `resolved` |
| `get_ticket` | `ticket_id` | `tickets`, `ticket_events` | R | One ticket plus its status history |
| `update_ticket` | `ticket_id`, `new_status`, `note`, `actor` | `tickets`, `ticket_events` | W | Sets status (`open` / `in_progress` / `waiting_on_human` / `resolved`) and logs who changed it and why |
| `get_stock_and_price` | `sku`, `size` | `inventory`, `pricing` | R | Units on hand, in-stock flag, aisle, unit cost, list price |
| `check_order_fill` | `sku`, `size`, `qty_requested` | `inventory` | R | How many can ship now and the shortfall |
| `evaluate_discount` | `sku`, `proposed_unit_price`, `qty` | `pricing` | R | Discount % off list, margin per unit and %, order totals, above-cost flag |
| `list_vendors` | — | `vendors`, `invoices` | R | Every vendor with lead days, open invoices and `can_ship` |
| `get_vendor_eta` | `vendor_id` | `vendors`, `invoices`, `desk` | R | `date_today + lead_days`; null if the vendor is on hold, plus the earliest date once the hold clears |
| `get_invoice_status` | `invoice_id` | `invoices`, `vendors`, `desk` | R | Amount, due date, status, overdue on `desk.date_today`, vendor details, whether the vendor can ship |
| `list_open_invoices` | — | `invoices`, `vendors`, `desk` | R | All unpaid invoices with overdue status and total owed |
| `get_lease_rent_status` | `lease_id` | `leases`, `cash_accounts`, `desk` | R | Rent, next due date, days until due / overdue, balances, whether cash covers rent |
| `get_cash_position` | — | `cash_accounts`, `payment_requests` | R | Balances, pending requests, **available cash** (balances − pending) |
| `request_payment` | `kind` (`invoice`/`rent`), `ref_id`, `requested_by`, `reason` | `invoices`, `leases`, `vendors`, `cash_accounts`, `payment_requests` | W (`payment_requests` only) | Files a request for **human approval**. The amount and payee come from the DB. Rejected as `rejected_insufficient_cash` if available cash is short; duplicates return the existing request |
| `list_payment_requests` | optional `status` | `payment_requests` | R | Payment requests filed so far |

No tool pays anything, changes balances, writes to `payments`, or sends any message. Payment approval belongs to a human.

## Running

The vibe coder starts it automatically from `.mcp.json`. To run it by hand:

```bash
.venv/Scripts/python.exe mcp_server/server.py
```
