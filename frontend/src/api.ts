// Thin client for the Campus Customs FastAPI backend.
import type { CashResponse, EventsResponse, Health, PaymentRequest, TicketsResponse } from './types'

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is uvicorn running?`)
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? `HTTP ${res.status}`)
  return body as T
}

export const api = {
  health: () => call<Health>('/api/health'),
  tickets: () => call<TicketsResponse>('/api/tickets'),
  cash: () => call<CashResponse>('/api/cash'),
  payments: () => call<{ count: number; requests: PaymentRequest[] }>('/api/payments'),
  events: (params: { run_id?: string; after?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params.run_id) q.set('run_id', params.run_id)
    if (params.after !== undefined) q.set('after', String(params.after))
    q.set('limit', String(params.limit ?? 2000))
    return call<EventsResponse>(`/api/events?${q}`)
  },
  runTicket: (id: number) =>
    call<{ run_id: string; ticket_id: number; status: string }>(`/api/tickets/${id}/run`, { method: 'POST' }),
  approve: (id: number, approvedBy: string) =>
    call<{ balance_before: number; balance_after: number; payee: string }>(`/api/payments/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy }),
    }),
  deny: (id: number, decidedBy: string, reason: string) =>
    call<unknown>(`/api/payments/${id}/deny`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: decidedBy, reason }),
    }),
}
