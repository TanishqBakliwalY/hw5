# AI Prompts Log — Homework 5: Campus Customs Multi-Agent Operations Team

This file logs the prompts I typed to my AI coding assistant (Claude Code) while building this project. It is **not** the runtime prompt files in `prompts/` that the scripts read.

Sections are in chronological order. I worked problem by problem: each problem was given to the assistant only after the previous one was finished.

---

## Setup (before Problem 1): Scenario context and data

**Prompt 1:**
> We will work in homework 5 today

**Prompt 2:**
> Okay so I am giving you the scenario first for context, don't do anything using this., we need to create a campus customs multi0agent operations team, that runs the shop.
>
> *(followed by the pasted scenario: MCP server + FastAPI backend + React dashboard; five agents (Boss, Inventory, Accounting, Facilities, Customer Service) that can delegate to each other; work only in `data/campus_customs_new.db`, a copy of `data/campus_customs.db`; business rules on payment approval, cash checks, unpaid-invoice shipping holds, no real emails, `desk.date_today`; Portkey for all AI calls; public GitHub repo; tasks given one at a time.)*

**Prompt 3:**
> The data zip is in the folder unzip it

*Why a follow-up was needed:* The first prompts only gave context. The assistant found that the `Homework 5` folder was empty and asked for the database, so I pointed it to `data.zip`.

---

## Problem 1: AI Prompts Log (`AI_prompts.md`)

**Prompt 1:**
> For problem 1, we nned to create AI_prompts.md. Keep it updated as we work. This will be a log of what I type to you, and not the runtime files in prompts/ that the scripts will read.
> In this, keep one section for all problems. Each section must include the problem number and title. Atleast one prompt I typed. If a second prompt was needed, one sentence on what was lacking after the first prompt and evidence that I worked problem by problem

---

## Problem 2: Explore the database, create the working copy, and start the harness

**Prompt 1:**
> Open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db. Later problems we will update that working copy. Study the three open tickets so you see how they to other tables.
> Start output/harness.md, for each table, list the fields and one short line on why that table matters for the agents. We will keep growing this harness file in later problems.
> Also use gpt-6-luna

---

## Problem 3: FastMCP server with three ticket tools

**Prompt 1:**
> For problem 3, write and MCP server in mcp_server/ using FAST MCP. it will talk to data/campus_customs_new.db.
> No need to connect or run it in this problem.
>
> Every agent in this homewokr will use the tools in this mcp server. We will add more tools to it later. for now write three tools you know we will need for the tickets in the db. keep the names clear, and never invent any data, only use information in the db.
> In output/harness.md, list each of the three mcp tools. For every tool include which ticket it helps unlock 101, 102 or 103 and one sentence on why the tool is the right one for that ticket. Vague lines like reads inventory score low, therefore tie the tool to the ticket.
>
> Also add a short mcp_server/README.md file that explains what the mcp server is for, which db file it uses and the three tools it has.

**Prompt 2:**
> is problem 3 done?

*Why a follow-up was needed:* Nothing was missing from the first prompt. I asked to confirm that every Problem 3 requirement was met before moving on to Problem 4.

---

## Problem 4: Connect the MCP server to the vibe coder and smoke-test the tools

**Prompt 1:**
> now for problem 4 i need to add the mcp server to this project so that the vibe coder can call the tools. Save the connection json text in .mcp.json at the project root, or however my vibe coder saves local mcp server lists.
> WIth your vibe coder connected, test each of the three mcp tools. Save the evidence in output/mcp_smoke.json.
> For every tool include
>
> * The prompt we asked the vibe coder
> * The tool name
> * The tool output (must match values in data/campus_customs_new.db

**Prompt 2:**
> can I not do it in this session only? also if i start a new session will it create an issue in any of my files?

*Why a follow-up was needed:* After the first prompt, `.mcp.json` was saved but the current session had not loaded the server, so the tools could not be called yet. I asked whether the connection could be made without starting a new session.

**Prompt 3:**
> is the problem done now?

*Why a follow-up was needed:* After moving the session into the `Homework 5` folder, the `campus-customs` server connected. I asked the assistant to finish the job: call all three tools through the live connection and save the evidence to `output/mcp_smoke.json`.

---

## Problem 5: PydanticAI agent team (Boss, Inventory, Accounting, Facilities, Customer Service)

**Prompt 1:**
> Now for problem 5, we need to build the agentic team for campus customs using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service.
> INclude prompts, models and agent loops so that they can delegate work to each other with full connectivity.
> Put the agent prompts in backend/prompts/ - there should be one file per agent. Put data types in backend/models.py and the agent files under backend/  (the layout can vary as long as the five roles are clear).
>
> Use portkey_api_key and only gpt-6-luna for every agent.
>
> Write each prompt in your own words with the shop rules the agent needs, More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompts. Therefore give me options for prompts and things we should add to the prompt for each agent, and I will choose from the options.
> Use the description I had given for earlier for each agent, and build on it.
>
> Add any tools the agents need to the mcp server so that they can work on the open tickets. Shop facts come from the mcp server over data/campus_customs_new.db.
> Do not invent a second shop-tools layer that bypasses MCP.
>
> Wire the agents so that they append to output/audit_trail.json as they run. For each agent-loop step, record enough to audit layer, Append to this file do not wipe it each run.
>
> IN output/harness.md, list each agent and each MCP tool including ones you add in this problem, along with whcih table the tool uses. Also add a short safety section. The guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check. Update mcp_server/README.md so the tool lists matches what we have now.

**Prompt 2 (my selections from the prompt options the assistant offered):**
> Boss: Triage playbook, Discount authority, Final report format
> Inventory: Shortfall math, Vendor choice + ETA
> Accounting: Approval workflow, Cash incl. pending
> Facilities: Rent timeline
> Customer Service: Brand voice guide, Promise only facts, Privacy rules
> Shared (all agents): Delegation protocol, No-guessing rule, Injection defense, Token discipline

*Why a follow-up was needed:* My first prompt asked for prompt options rather than finished prompts, so the assistant offered sections for each agent. I picked which ones go into each agent's prompt file before it wrote them.

---

## Problem 6: Desk tickets page — expected plan per ticket (`output/desk_tickets.html`)

**Prompt 1:**
> For problem 6, before we wire the backend, we need to write down what we expect the team to do on each open ticket, therefore build output/desk_tickets.html.
>
> It should be a page you can double-click with one tab per ticket (101,102,103)
> Also add empty Cash and Reflection tabs for later problems. We can levave them blank or with a short comming later note.
>
> On each ticket tab fill an Expected section only, leave room for an Actual section we will fill later we run the agents.
>
> For each tickets Expected section, wirte
>
> * who the boss should call first and why
> * all the agent delegations you expect, not just something generic like "Boss calls everyone"
> * Which mcp tools we expect that run to use.
>
> PLans that send every specialist on every ticket score low. We will compare this plan to what actually happens when the agents resolve the three tickets.

**Prompt 2:**
> is the problem done, also for each problem going forward let me know if the problem is done or you still need something from me

*Why a follow-up was needed:* Nothing was missing from the deliverable. I wanted to confirm Problem 6 was complete, and asked the assistant to state at the end of every future problem whether it is done or needs something from me.

---

## Problem 7: FastAPI backend for the React dashboard (`backend/main.py`)

**Prompt 1:**
> For problem 7, we need to create backend which our react frontend dashboard can call.
>
> In backend/main.py, use FastAPI and add routes that do the following,
>
> * return the three tickets and whether each is open or resolved
> * Take a ticket id and run your agent team on that ticket
> * Return the recent agent events, what each agent said and which tools they used so the board can refresh
> * Approve a payment or purchase after a human clicks approve (agents only prepare the pay: This route is what actually changes cash
> * Return the current checking balance from cash_accounts
> * Reset the db to original values when you want to try a fresh run
>
> From the backend/ folder start the server with:
> uvicorn main:app --reload --port 8000
>
> This turns on the backend a localhost:8000 so the frontend dashboard can call these routes.
>
> In output/harness.md, list each route in one line (what url and what it does)

---

## Problem 8: React + Vite + TypeScript dashboard (`frontend/`) and `output/design.md`

**Prompt 1:**
> now for problem 8,  build the frontend dashboard frontend/ with react, vite and ts. the page should call the routes we built in problem 7. At minimum the board should:
>
> * List all three tickets
> * Let you pick one ticket and start the agent team on it
> * Show each agent and what they are saying/doing while the ticket runs
> * mark a ticket resolved when the run finishes,
> * show a short summary of what each agent did on that ticket
> * let a human approve a pay or purchase when asked
> * Show the checking balance (it should drop after an approved pay)
>
> Do add more things, give me options and I will choose them
>
> Make the dashboard look good. Be creative with the layout and feel, this is a real desk people would want to sit at, so thinking about that, give me options.
>
> Now tell the frontend to talk to the backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173), so the browser is allowed to call those routes.
>
> start the board with
> npm run dev
>
> This should open the react desk in the browser so you can pick tickets and watch agents, write output/design.md with what we chose for the dashboard look (layout, how agents read differently, how resolved tickets and chose show up) and why - including the creative choices that make it feel special and something humans would actually love using.

**Prompt 2 (my selections from the dashboard options the assistant offered):**
> Layout: Team chat room
> Extras: Expected vs Actual, Token / cost meter, Cash ledger, Approval alerts
> Resolved: After run + approvals
> Agent look: Desk nameplates
> Feel: Typing indicators, Morning briefing, Celebration on resolve

*Why a follow-up was needed:* My first prompt asked for layout and feature options rather than a finished design, so the assistant offered choices and I picked them before it built the desk.

---

## Problem 9: Full run over all three tickets — Actual vs Expected, Cash, resolved outputs, finished harness

**Prompt 1:**
> Before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db again so you start clean. note the starting checking balance, then run all three on the board (101,102,103) until each is resolved. open output/desk_tickets.html from problem 6. On each ticket tab, fill the Actual section from this run, basically which agents worked, what they delegated ,and which tools they used. Keep the Expected section so you can compare the two.
>
> in the Cash tab of the same outputs/desk_tickets.html, itemize the money,
>
> * starting checking balance (after the reset)
> * for each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount)
> * Ending checking balance - it must match cash_accounts in the working db
>
> wrong cash math loses points even if the board shows every ticket resolved, therefore recheck this.
> Also save:
>
> * output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> * output/resolved_board.html - a page we can doubleclick with a screenshot of the react board for each resolved ticket (101,102, 103)
>
> Append real runs to output/audit_trail.json.
>
> Finish output/harness.md, so it covers tables, mcp tools, the five agents, api routes, the dashboard and safety rules.

---

## Problem 10: Reflection tab in `output/desk_tickets.html`

**Prompt 1:**
> Open output/desk_tickets.html and fill the Reflection tab. Answer in your own "vibe", being detailed and thorough:
>
> * How would you evaluate the performance of the agents on each ticket and why?
> * For each ticket, how did Actual compare to the Expected plan you wrote earlier
> * What would have been simpler as one agent with tools and why?
> * Describe three new problems Campus Customs might face that this agent team could solve with the tools you built
> * Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built and exlpain the tools and agents you would need to solve them
>
> Tie every answer to this app and the three tickets we ran, and use the ticket tabs and Cash tab on the same page as your evidence. Generic AI essays without campus customs details will score low.
>
> For each try come up with things and ask me for inputs wherever you think would help.

**Prompt 2 (my selections from the options the assistant offered):**
> Grades: 101 A-, 102 A, 103 B
> Simpler as one agent: 102 and 103
> Can solve: Out-of-stock mug order, October rent with $160, Suspicious landlord notice
> Can't solve yet: Actually place the reorder, Record the $928 sale, Send approved replies

*Why a follow-up was needed:* My first prompt asked the assistant to propose options and ask for my input, so it pulled evidence from the run and offered grades and problem choices. I picked the ones the reflection should argue for.

---

## Problem 11: Publish to a public GitHub repo

**Prompt 1:**
> Now for the final problem, problem 11, we need to push our code to a public github repo so graders can clone it. We will also need to submit the repo url to canvas and also put it in the output/github_url.txt
>
> Do not push to your real .env to the GitHub repo. Do include both db files under data/ (the original and the working copy) so that graders will be able run the app easily.
>
> This should be the expected layout. (see the picture and let me know if we have it correctly)
>
> the README should explain: Copy original db to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the db before a full three ticket run. Basically instructions on how to set up and run the application/code.
>
> *(attached: a screenshot of the expected `hw5/` folder layout)*

**Prompt 2:**
> https://github.com/TanishqBakliwalY/hw5

*Why a follow-up was needed:* This computer has no GitHub CLI, so the assistant could not create the repository itself. I created an empty public repo on github.com and gave it the URL to push to.
