// Shapes returned by the FastAPI backend (backend/main.py).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export type TicketStatus = 'open' | 'in_progress' | 'waiting_on_human' | 'resolved'
export type RequestStatus = 'pending_approval' | 'approved' | 'denied' | 'rejected_insufficient_cash'

export interface PaymentRequest {
  id: number
  kind: 'invoice' | 'rent'
  ref_id: number
  payee: string
  amount: number
  reason: string | null
  requested_by: string
  requested_on: string
  status: RequestStatus
  decided_by: string | null
  decided_at: string | null
}

export interface Fact { statement: string; source: string }
export interface HumanAction {
  kind: 'approve_payment' | 'approve_discount' | 'decision'
  description: string
  ticket_id: number | null
  payment_request_id: number | null
}
export interface DraftMessage { recipient: string; subject: string; body: string; ticket_id: number | null }

export interface AgentReport {
  agent: AgentName
  summary: string
  facts: Fact[]
  actions_taken: string[]
  human_actions_needed: HumanAction[]
  drafts: DraftMessage[]
  open_questions: string[]
}

export interface TicketOutcome {
  ticket_id: number
  ticket_type: string
  status: TicketStatus
  agents_involved: AgentName[]
  summary: string
  human_actions_needed: HumanAction[]
  drafts: DraftMessage[]
  next_steps: string[]
}

export interface BossReport {
  shop_date: string
  tickets: TicketOutcome[]
  cash_summary: string
  notes: string[]
}

export interface RunUsage { input_tokens: number; output_tokens: number; requests: number; tool_calls: number }

export interface LastRun {
  run_id: string
  ticket_id: number
  started_at: string
  finished_at: string | null
  status: 'running' | 'completed' | 'failed' | 'interrupted'
  usage: RunUsage | null
  boss_report: BossReport | null
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: TicketStatus
  notes: string | null
  created_at: string
  state: 'open' | 'resolved'
  payment_requests: PaymentRequest[]
  pending_approvals: number
  last_run: LastRun | null
  running: boolean
}

export interface TicketsResponse {
  date_today: string
  open_count: number
  resolved_count: number
  current_run: string | null
  tickets: Ticket[]
}

export interface Payment {
  id: number
  kind: string
  ref_id: number
  amount: number
  account: string
  paid_at: string
  approved_by: string
}

export interface CashResponse {
  date_today: string
  account: string
  balance: number
  balance_as_of: string
  pending_requests: number
  pending_total: number
  available_after_pending: number
  payments: Payment[]
}

export interface FeedEvent {
  id: number
  ts: string
  run_id: string
  seq: number
  layer: 'run' | 'agent' | 'llm' | 'mcp' | 'delegation' | 'human'
  event: string
  agent: AgentName | null
  depth: number | null
  ticket_id: number | null
  text: string
  said: string | null
  tools: string[]
  usage: Partial<RunUsage> | null
  meta: {
    tool?: string
    tool_call_id?: string
    args?: Record<string, unknown>
    ms?: number
    to_agent?: AgentName
    task?: string
    reason?: string
    why?: string
    output?: AgentReport | BossReport
    steps?: number
  }
}

export interface EventsResponse {
  total_events: number
  next_after: number
  count: number
  events: FeedEvent[]
}

export interface Health {
  ok: boolean
  model: string
  database: string
  current_run: string | null
  limits: { requests: number; tool_calls: number; total_tokens: number; max_delegation_depth: number }
}
