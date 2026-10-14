# Campus Customs Desk — Design

The dashboard in `frontend/` (React + Vite + TypeScript) is the human side of the five-agent team. `npm run dev` opens it at `http://localhost:5173`, and it calls the FastAPI backend at `http://localhost:8000` (`VITE_API_BASE` overrides that). The backend lets the Vite origin through CORS (`http://localhost:5173` and `http://127.0.0.1:5173`).

All of the choices below were picked from the options offered:

| Decision | Chosen | Not chosen |
|---|---|---|
| Layout | **Team chat room** | Mission Control, Shop-floor Kanban, Trading terminal |
| How agents read differently | **Desk nameplates** | Color + monogram only, emoji characters |
| Finishing touches | **Typing indicators, Morning briefing, Celebration on resolve** | Hand-off threads as a separate feature (depth indentation is still used) |
| Extras | **Expected vs Actual, Token / cost meter, Cash ledger, Approval alerts** | Drafts inbox (drafts live inside the chat instead), Reset + run-all, Keyboard shortcuts, Run history |
| When a ticket is "resolved" | **After the run *and* its approvals** | Immediately when the run finishes |

---

## 1. Layout: a team chat room

```
┌ Morning briefing: greeting · shop date · open · waiting on you · checking · resolved · "approving as" ┐
├ Nameplates:  [B Boss] [I Inventory] [A Accounting] [F Facilities] [CS Customer Service]              ┤
├──────────────┬──────────────────────────────────────────────────────┬──────────────────────────┤
│ # ticket-101 │ #ticket-101 · Bulldog tee          [Needs you] [Run ▸] │ CHECKING  $3,400.00      │
│ # ticket-102 │  ── Ticket handed to the team ──                       │ ▁▂▃ sparkline            │
│ # ticket-103 │  B Boss  ⟶ @Inventory  "can we fill 1×S?"             │ waiting on you · ledger  │
│   (channels) │    I Inventory  ✓ order fill ✓ vendor ETA              │──────────────────────────│
│              │      I → @Accounting "file invoice 501"                │ Plan vs actual │ Run meter│
│              │        A Accounting  report: request #1 filed          │                          │
│              │  B Boss  wrap-up · next steps · drafted replies        │                          │
│              │  Shift report: who did what                            │                          │
│              │ ┌ ACTION NEEDED  Pay Bulldog Print Co $840 [Approve] ┐ │                          │
└──────────────┴──────────────────────────────────────────────────────┴──────────────────────────┘
```

**Why a chat room:** a run is a conversation. The Boss asks, specialists answer, someone hands work on. A chat transcript is the format people already read fluently, at a glance, all day. Each ticket is a **channel** (`#ticket-101`), so picking a ticket feels like opening a thread, and the left rail doubles as an inbox with status pills and amber "needs you" badges. The center is the conversation. The right column holds what a manager keeps glancing at: **money** (always visible) and the **plan / meter** tabs.

## 2. How the agents read differently: desk nameplates

- **A row of nameplates across the top**, one per agent, like name blocks on a real desk. Each has a monogram tile (B, I, A, F, CS), the agent's name, a job title ("Stock & Vendors", "Cash & Payments"…) and a live status line: *at desk*, *thinking*, *using order fill*, *waiting on Accounting*, *done*.
- **The working agent's plate lights up:** it lifts slightly, its border glows in the agent's accent, and the brass strip under the plate pulses. Agents not involved in a ticket stay dimmed at their desks, so you see at a glance that the Boss didn't wake Facilities for a tee order.
- **Every message "hangs" from its plate:** the same monogram, accent color and name appear on the message, and a vertical rail in that color runs down the left of the bubble.
- **One accent per desk, on a black-and-green base:** Boss green `#4ade80`, Inventory teal `#2dd4bf`, Accounting gold `#facc15` (money), Facilities sky `#7dd3fc`, Customer Service orchid `#f0abfc`. The shell stays black and green (the class theme); color is only used to tell people apart.
- **Message shapes differ by kind:**
  - *Hand-offs* are dashed bubbles with an `@Agent` mention in the receiver's color, plus the one-line *why*.
  - *Work* is a row of **tool chips** (`order fill`, `vendor ETA`…) that spin while the MCP call runs and tick with the latency in ms when it returns.
  - *Reports* show the summary, a ✓ list of actions taken, and a collapsible "facts with sources".
  - The Boss's *wrap-up* is a highlighted card with next steps and the drafted replies (marked **never sent — for your review**, with a copy button).
- **Delegation depth becomes indentation:** Boss → Inventory → Accounting steps inward, so you can see who asked whom without a diagram.

## 3. Watching a run live

- **Typing indicators:** while an agent waits on the model, its plate shows animated dots and a "Inventory is thinking…" line appears at the bottom of the channel.
- The channel polls `GET /api/events?run_id=…&after=…` every 1.2 s and only appends new events, so the conversation streams in. It auto-scrolls while live and stops once the run ends.
- **Run meter** (the tab opens itself when a run starts): a run clock, plus bars for model calls, tool calls and tokens against the team's hard limits (60 / 80 / 250k). The bars turn amber, then red, as they fill, which makes the token budget something a manager can actually see.

## 4. Resolved tickets and choices that need a human

- **Resolved means the work is actually finished.** When the run ends, the backend links every payment request the run raised (or depends on) to the ticket. The ticket shows **Needs you** (amber) until each of those requests is approved, denied or rejected, then flips to **Resolved** on its own. A ticket that needs no payment resolves as soon as the run ends.
- **Action-needed cards dock at the bottom of the channel,** above the fold, in amber with a vertical *ACTION NEEDED* flag. Each shows the payee, amount, what it pays (invoice 501, rent for lease 1), who requested it, and the agent's reason in quotes, with **Approve & pay** and **Deny** buttons. Nothing moves money except that button, which calls `POST /api/payments/{id}/approve`, the only route that changes cash.
- **Only a person can approve.** The "Approving as" field in the header must hold a human name. Agent names are refused, and the backend checks this too. The name is remembered on this computer.
- **After a decision, the card becomes a receipt** in the channel history: green "Paid $840 → Bulldog Print Co", or red "Rejected — not enough cash" / "Denied".
- **Resolved tickets get a celebration:** a rubber **RESOLVED stamp** thumps onto the channel header, a short burst of green confetti falls, the channel's subject is struck through in the rail with a ✓, and a toast says "Ticket 101 resolved — nice work." It's subtle, it's brief, and it's earned. Motion respects `prefers-reduced-motion`.

## 5. Money you can feel

- **Checking appears twice**, as a big number in the cash card and a stat in the briefing. When a payment is approved, the figure **rolls down** to the new balance and glows amber for a moment, so the drop is impossible to miss.
- **Sparkline + ledger:** the line shows the balance after each payment. The ledger lists every payment (date, approver, running balance), each pending request (◷ waiting on you), and rejected or denied requests (struck through). "Left if you approve all" warns you before you commit cash that two tickets are both drawing on.
- **Approval alerts:** when an agent files a new request, a soft two-note chime plays (after your first click, as browsers require), a toast names the payee and amount, and the browser tab title becomes **"(1) Needs you · Campus Customs Desk"**. You can look away during a 90-second run and still know when you're needed.

## 6. Expected vs Actual

The **Plan vs actual** tab puts the Problem 6 plan (`output/desk_tickets.html`) next to what the run really did:

- **Boss calls first:** expected vs actual, with a ✓ or ✗.
- **Hand-offs:** each planned delegation is ticked as it happens. Unplanned ones appear in amber as "+ Boss → Facilities · not in plan". "Not called" agents turn red if they were called.
- **MCP tools per agent:** planned tools go green when used and red if the run ended without them. Extra lookups appear as dashed chips.
- **Score line:** "3/3 planned hand-offs happened".

This makes the agents' judgement auditable. It's the same comparison the Actual section of `desk_tickets.html` will hold, but live.

## 7. Morning briefing

The header greets you by name and time of day ("Good afternoon, Tanishq.") and states the **shop's** date from `desk.date_today` ("At the shop it's Monday, August 31, 2026"), because every overdue judgement uses that date, not the computer's clock. Next to it are four tiles: open tickets, **waiting on you** (amber when anything is pending, with dollars and ticket count), checking, and resolved. A small green or red dot shows whether the backend is reachable.

## Why people would love sitting at it

- **It reads like a team, not a log.** You watch colleagues talk, hand off and report back, and every line names who said it.
- **Calm by default, loud only when it matters.** It's dark and quiet, with motion reserved for live work (glowing plates, spinning chips) and for your decisions (amber cards, a chime, a rolling balance, the resolved stamp).
- **You are clearly the one in charge.** Agents prepare; the human approves. The only red-and-amber elements on the page are things that need you.
- **Nothing is hidden.** Facts carry their sources, drafts are readable and copyable, the plan sits next to the reality, and the token meter shows what the run cost.

## Files

| Path | What it is |
|---|---|
| `frontend/src/App.tsx` | State, polling, run / approve / deny actions, alerts, celebration trigger |
| `frontend/src/components/Briefing.tsx` | Morning briefing header and the "approving as" name |
| `frontend/src/components/Nameplates.tsx` | The five desk nameplates with live status |
| `frontend/src/components/ChannelList.tsx` | Ticket channels with status pills and badges |
| `frontend/src/components/Channel.tsx` | Chat feed, tool chips, hand-offs, reports, wrap-up, shift report, action cards, stamp and confetti |
| `frontend/src/components/SidePanel.tsx` | Cash card (sparkline and ledger), Plan vs actual, Run meter |
| `frontend/src/lib/feed.ts` | Turns audit events into messages, nameplate states and per-agent summaries |
| `frontend/src/lib/expected.ts` | The Problem 6 plan as data |
| `frontend/src/api.ts` | Client for `http://localhost:8000` |
| `frontend/src/index.css` | The look: black-and-green desk, per-agent accents, motion |
