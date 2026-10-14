// The plan written before the backend existed (output/desk_tickets.html, Problem 6).
import type { AgentName } from '../types'

export interface ExpectedPlan {
  firstCall: AgentName
  why: string
  delegations: [AgentName, AgentName][]
  optional?: [AgentName, AgentName][]
  notCalled: AgentName[]
  tools: Partial<Record<AgentName, string[]>>
}

export const EXPECTED: Record<number, ExpectedPlan> = {
  101: {
    firstCall: 'inventory',
    why: 'A customer order starts with “can the shelf fill it?”',
    delegations: [['boss', 'inventory'], ['inventory', 'accounting'], ['boss', 'customer_service']],
    notCalled: ['facilities'],
    tools: {
      boss: ['get_ticket', 'update_ticket'],
      inventory: ['check_order_fill', 'get_vendor_eta', 'get_invoice_status', 'list_payment_requests'],
      accounting: ['get_cash_position', 'request_payment'],
      customer_service: [],
    },
  },
  102: {
    firstCall: 'facilities',
    why: 'A rent notice is checked against the lease before money moves.',
    delegations: [['boss', 'facilities'], ['facilities', 'accounting']],
    optional: [['boss', 'customer_service']],
    notCalled: ['inventory'],
    tools: {
      boss: ['get_ticket', 'update_ticket'],
      facilities: ['get_lease_rent_status', 'list_payment_requests'],
      accounting: ['get_cash_position', 'request_payment'],
    },
  },
  103: {
    firstCall: 'inventory',
    why: 'A discount only matters if 20 hoodies can be delivered.',
    delegations: [['boss', 'inventory'], ['boss', 'customer_service']],
    notCalled: ['facilities', 'accounting'],
    tools: {
      boss: ['get_ticket', 'evaluate_discount', 'update_ticket'],
      inventory: ['check_order_fill', 'get_vendor_eta', 'list_payment_requests'],
      customer_service: [],
    },
  },
}
