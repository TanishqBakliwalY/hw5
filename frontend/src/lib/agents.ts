import type { AgentName } from '../types'

export interface AgentMeta {
  name: AgentName
  label: string
  title: string
  initials: string
  color: string // accent used for the nameplate, message rail and chips
}

// One accent per desk so agents are told apart at a glance; all sit on the black/green base.
export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: { name: 'boss', label: 'Boss', title: 'Operations Lead', initials: 'B', color: '#4ade80' },
  inventory: { name: 'inventory', label: 'Inventory', title: 'Stock & Vendors', initials: 'I', color: '#2dd4bf' },
  accounting: { name: 'accounting', label: 'Accounting', title: 'Cash & Payments', initials: 'A', color: '#facc15' },
  facilities: { name: 'facilities', label: 'Facilities', title: 'Lease & Space', initials: 'F', color: '#7dd3fc' },
  customer_service: {
    name: 'customer_service', label: 'Customer Service', title: 'Drafts & Replies', initials: 'CS', color: '#f0abfc',
  },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TOOL_LABELS: Record<string, string> = {
  get_shop_date: 'shop date',
  list_open_tickets: 'open tickets',
  get_ticket: 'read ticket',
  update_ticket: 'update ticket',
  get_stock_and_price: 'stock & price',
  check_order_fill: 'order fill',
  evaluate_discount: 'discount check',
  list_vendors: 'vendors',
  get_vendor_eta: 'vendor ETA',
  get_invoice_status: 'invoice status',
  list_open_invoices: 'open invoices',
  get_lease_rent_status: 'lease & rent',
  get_cash_position: 'cash position',
  request_payment: 'request payment',
  list_payment_requests: 'payment requests',
  delegate: 'hand-off',
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
