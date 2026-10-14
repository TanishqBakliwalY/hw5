import { useEffect, useState } from 'react'
import type { AgentName, CashResponse, Health, PaymentRequest } from '../types'
import { AGENTS, TOOL_LABELS, money } from '../lib/agents'
import { EXPECTED } from '../lib/expected'
import type { Digest } from '../lib/feed'
import { RollingMoney, Sparkline } from '../lib/ui'

function CashCard({ cash, requests }: { cash: CashResponse | null; requests: PaymentRequest[] }) {
  if (!cash) return <div className="card cash-card">Loading cash…</div>
  const paidTotal = cash.payments.reduce((s, p) => s + p.amount, 0)
  const points = [cash.balance + paidTotal]
  for (const p of cash.payments) points.push(points[points.length - 1] - p.amount)
  const pending = requests.filter((r) => r.status === 'pending_approval')
  const rejected = requests.filter((r) => r.status === 'rejected_insufficient_cash' || r.status === 'denied')

  return (
    <div className="card cash-card">
      <div className="card-head">Checking <span>as of {cash.balance_as_of}</span></div>
      <RollingMoney value={cash.balance} className="cash-big" />
      <Sparkline points={points} />
      <div className="cash-row"><span>Waiting on you</span><b className="amber">{money(cash.pending_total)}</b></div>
      <div className="cash-row"><span>Left if you approve all</span><b>{money(cash.available_after_pending)}</b></div>

      <div className="ledger">
        <div className="ledger-head">Ledger</div>
        {cash.payments.length === 0 && pending.length === 0 && rejected.length === 0 && (
          <div className="ledger-empty">No money has moved yet.</div>
        )}
        {cash.payments.map((p, i) => (
          <div key={`p${p.id}`} className="ledger-row paid">
            <span className="ledger-what">{p.kind === 'invoice' ? `Invoice ${p.ref_id}` : `Rent · lease ${p.ref_id}`}</span>
            <span className="ledger-amt">−{money(p.amount)}</span>
            <span className="ledger-meta">{p.paid_at} · approved by {p.approved_by} · bal {money(points[i + 1])}</span>
          </div>
        ))}
        {pending.map((r) => (
          <div key={`r${r.id}`} className="ledger-row pending">
            <span className="ledger-what">{r.payee}</span>
            <span className="ledger-amt">{money(r.amount)}</span>
            <span className="ledger-meta">request #{r.id} · pending your approval</span>
          </div>
        ))}
        {rejected.map((r) => (
          <div key={`x${r.id}`} className="ledger-row rejected">
            <span className="ledger-what">{r.payee}</span>
            <span className="ledger-amt">{money(r.amount)}</span>
            <span className="ledger-meta">request #{r.id} · {r.status === 'denied' ? 'denied' : 'rejected: not enough cash'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Mark({ ok, pending }: { ok: boolean; pending: boolean }) {
  if (pending) return <span className="mark mark-wait">…</span>
  return ok ? <span className="mark mark-ok">✓</span> : <span className="mark mark-miss">✗</span>
}

function PlanVsActual({ ticketId, digest, hasRun }: { ticketId: number; digest: Digest; hasRun: boolean }) {
  const plan = EXPECTED[ticketId]
  if (!plan) return <div className="muted">No plan written for this ticket.</div>
  const key = (d: [AgentName, AgentName]) => `${d[0]}>${d[1]}`
  const actual = digest.delegations.map(key)
  const actualSet = new Set(actual)
  const planned = new Set(plan.delegations.map(key))
  const optional = new Set((plan.optional ?? []).map(key))
  const extras = [...actualSet].filter((k) => !planned.has(k))
  const firstActual = digest.delegations.find(([from]) => from === 'boss')?.[1]
  const waiting = !digest.finished
  const label = (n: AgentName) => AGENTS[n].label

  const matched = plan.delegations.filter((d) => actualSet.has(key(d))).length
  return (
    <div className="plan">
      {hasRun && digest.finished && (
        <div className="plan-score">
          {matched}/{plan.delegations.length} planned hand-offs happened
          {extras.filter((k) => !optional.has(k)).length > 0 ? ` · ${extras.filter((k) => !optional.has(k)).length} unplanned` : ''}
        </div>
      )}
      <div className="plan-block">
        <div className="plan-k">Boss calls first</div>
        <div className="plan-row">
          <span>Expected <b style={{ color: AGENTS[plan.firstCall].color }}>{label(plan.firstCall)}</b></span>
          <span>
            Actual {firstActual ? <b style={{ color: AGENTS[firstActual].color }}>{label(firstActual)}</b> : <span className="muted">—</span>}
            {hasRun && <Mark ok={firstActual === plan.firstCall} pending={!firstActual && waiting} />}
          </span>
        </div>
        <div className="plan-why">{plan.why}</div>
      </div>

      <div className="plan-block">
        <div className="plan-k">Hand-offs</div>
        {plan.delegations.map((d) => (
          <div key={key(d)} className="plan-row">
            <span>{label(d[0])} → {label(d[1])}</span>
            {hasRun && <Mark ok={actualSet.has(key(d))} pending={!actualSet.has(key(d)) && waiting} />}
          </div>
        ))}
        {(plan.optional ?? []).map((d) => (
          <div key={key(d)} className="plan-row optional">
            <span>{label(d[0])} → {label(d[1])} <small>optional</small></span>
            {hasRun && actualSet.has(key(d)) && <span className="mark mark-ok">✓</span>}
          </div>
        ))}
        {extras.filter((k) => !optional.has(k)).map((k) => {
          const [a, b] = k.split('>') as [AgentName, AgentName]
          return <div key={k} className="plan-row extra"><span>+ {label(a)} → {label(b)}</span><small>not in plan</small></div>
        })}
        <div className="plan-not">
          Not called: {plan.notCalled.map((n) => {
            const called = digest.delegations.some(([, to]) => to === n)
            return <span key={n} className={hasRun && called ? 'bad' : ''}>{label(n)}{hasRun && called ? ' (was called)' : ''}</span>
          })}
        </div>
      </div>

      <div className="plan-block">
        <div className="plan-k">MCP tools</div>
        {(Object.entries(plan.tools) as [AgentName, string[]][]).map(([agent, tools]) => {
          const used = digest.toolsByAgent[agent] ?? new Set<string>()
          const extra = [...used].filter((t) => !tools.includes(t) && t !== 'delegate')
          return (
            <div key={agent} className="plan-tools">
              <span className="plan-agent" style={{ color: AGENTS[agent].color }}>{AGENTS[agent].label}</span>
              <div className="plan-chips">
                {tools.length === 0 && <span className="tchip">none needed</span>}
                {tools.map((t) => (
                  <span key={t} className={`tchip ${hasRun ? (used.has(t) ? 'tchip-ok' : waiting ? '' : 'tchip-miss') : ''}`}>
                    {TOOL_LABELS[t] ?? t}
                  </span>
                ))}
                {hasRun && extra.map((t) => <span key={t} className="tchip tchip-extra">+{TOOL_LABELS[t] ?? t}</span>)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Meter({ label, value, max, fmt }: { label: string; value: number; max: number; fmt?: (n: number) => string }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="meter">
      <div className="meter-top"><span>{label}</span><span>{fmt ? fmt(value) : value} / {fmt ? fmt(max) : max}</span></div>
      <div className="meter-bar"><i style={{ width: `${pct}%` }} className={pct > 85 ? 'hot' : pct > 60 ? 'warm' : ''} /></div>
    </div>
  )
}

function RunMeter({ digest, health, live }: { digest: Digest; health: Health | null; live: boolean }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (!live) return
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [live])
  const start = digest.startedAt ? Date.parse(digest.startedAt) : null
  const end = digest.endedAt ? Date.parse(digest.endedAt) : now
  const secs = start ? Math.max(0, Math.round((end - start) / 1000)) : 0
  const L = health?.limits ?? { requests: 60, tool_calls: 80, total_tokens: 250000, max_delegation_depth: 3 }
  const tokens = digest.usage.inputTokens + digest.usage.outputTokens
  const k = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 100000 ? 0 : 1)}k` : String(n))
  return (
    <div className="run-meter">
      <div className="meter-clock">{start ? `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}` : '0:00'}<small>{live ? 'running' : start ? 'run time' : 'no run yet'}</small></div>
      <Meter label="Model calls" value={digest.usage.requests} max={L.requests} />
      <Meter label="Tool calls" value={digest.usage.toolCalls} max={L.tool_calls} />
      <Meter label="Tokens" value={tokens} max={L.total_tokens} fmt={k} />
      <div className="meter-foot">
        {k(digest.usage.inputTokens)} in · {k(digest.usage.outputTokens)} out · {health?.model ?? 'gpt-6-luna'} via Portkey
        <br />The run stops itself if any bar fills.
      </div>
    </div>
  )
}

export function SidePanel(p: {
  cash: CashResponse | null
  requests: PaymentRequest[]
  ticketId: number | null
  digest: Digest
  hasRun: boolean
  health: Health | null
  live: boolean
}) {
  const [tab, setTab] = useState<'plan' | 'meter'>('plan')
  useEffect(() => { if (p.live) setTab('meter') }, [p.live])
  return (
    <aside className="side">
      <CashCard cash={p.cash} requests={p.requests} />
      <div className="card">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={tab === 'plan'} onClick={() => setTab('plan')}>Plan vs actual</button>
          <button role="tab" aria-selected={tab === 'meter'} onClick={() => setTab('meter')}>Run meter</button>
        </div>
        {p.ticketId === null ? <div className="muted">Pick a ticket.</div>
          : tab === 'plan' ? <PlanVsActual ticketId={p.ticketId} digest={p.digest} hasRun={p.hasRun} />
          : <RunMeter digest={p.digest} health={p.health} live={p.live} />}
      </div>
    </aside>
  )
}
