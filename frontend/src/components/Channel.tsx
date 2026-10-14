import { useEffect, useRef, useState } from 'react'
import type { AgentName, PaymentRequest, Ticket } from '../types'
import { AGENTS, TOOL_LABELS, money } from '../lib/agents'
import type { Digest, Message } from '../lib/feed'
import { clock } from '../lib/ui'

interface Props {
  ticket: Ticket
  digest: Digest
  live: boolean
  canRun: boolean
  runBlockedReason: string | null
  onRun: () => void
  requests: PaymentRequest[]
  onApprove: (r: PaymentRequest) => void
  onDeny: (r: PaymentRequest) => void
  busyRequest: number | null
  celebrate: boolean
}

function Who({ agent, ts, tag }: { agent: AgentName; ts: string; tag?: string }) {
  const a = AGENTS[agent]
  return (
    <div className="who" style={{ ['--agent' as string]: a.color }}>
      <span className="who-mono">{a.initials}</span>
      <span className="who-name">{a.label}</span>
      {tag && <span className="who-tag">{tag}</span>}
      <span className="who-time">{clock(ts)}</span>
    </div>
  )
}

function Clamp({ text, lines = 3 }: { text: string; lines?: number }) {
  const [open, setOpen] = useState(false)
  const long = text.length > 220
  return (
    <div className="clamp">
      <p className={!open && long ? 'clamped' : ''} style={{ ['--lines' as string]: lines }}>{text}</p>
      {long && <button className="link" onClick={() => setOpen(!open)}>{open ? 'less' : 'more'}</button>}
    </div>
  )
}

function MessageView({ m, ticketId }: { m: Message; ticketId: number }) {
  if (m.kind === 'system') {
    return <div className={`sys sys-${m.tone}`}><span>{m.text}</span><time>{clock(m.ts)}</time></div>
  }
  if (m.kind === 'final') {
    const t = m.output.tickets.find((x) => x.ticket_id === ticketId) ?? m.output.tickets[0]
    return (
      <div className="msg msg-final" style={{ ['--agent' as string]: AGENTS.boss.color }}>
        <Who agent="boss" ts={m.ts} tag="wrap-up" />
        <div className="bubble">
          {t ? (
            <>
              <p>{t.summary}</p>
              {t.next_steps.length > 0 && (
                <>
                  <div className="mini-head">Next steps</div>
                  <ul>{t.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
              {t.drafts.length > 0 && (
                <>
                  <div className="mini-head">Drafted replies <span className="never">never sent — for your review</span></div>
                  {t.drafts.map((d, i) => (
                    <details key={i} className="draft">
                      <summary>To <b>{d.recipient}</b> · {d.subject}</summary>
                      <pre>{d.body}</pre>
                      <button className="link" onClick={() => void navigator.clipboard.writeText(d.body)}>copy text</button>
                    </details>
                  ))}
                </>
              )}
            </>
          ) : <p>{m.output.cash_summary}</p>}
        </div>
      </div>
    )
  }

  const depth = 'depth' in m ? m.depth : 0
  const agent = m.kind === 'handoff' ? m.from : m.agent
  const style = { ['--agent' as string]: AGENTS[agent].color, ['--depth' as string]: depth }

  if (m.kind === 'handoff') {
    const to = AGENTS[m.to]
    return (
      <div className="msg msg-handoff" style={style}>
        <Who agent={agent} ts={m.ts} tag="hand-off" />
        <div className="bubble">
          <span className="mention" style={{ ['--to' as string]: to.color }}>@{to.label}</span>
          <Clamp text={m.task} />
          {m.reason && <div className="why">why: {m.reason}</div>}
        </div>
      </div>
    )
  }
  if (m.kind === 'work') {
    return (
      <div className="msg msg-work" style={style}>
        <Who agent={agent} ts={m.ts} tag="checking the books" />
        <div className="chips">
          {m.chips.map((c) => (
            <span key={c.key} className={`chip ${c.done ? 'chip-done' : 'chip-run'}`} title={c.tool}>
              <i>{c.done ? '✓' : ''}</i>
              {TOOL_LABELS[c.tool] ?? c.tool}
              {c.done && c.ms !== undefined && <small>{c.ms}ms</small>}
            </span>
          ))}
        </div>
      </div>
    )
  }
  if (m.kind === 'say') {
    return (
      <div className="msg" style={style}>
        <Who agent={agent} ts={m.ts} />
        <div className="bubble"><Clamp text={m.text} /></div>
      </div>
    )
  }
  // report from a teammate
  const o = m.output
  return (
    <div className="msg msg-report" style={style}>
      <Who agent={agent} ts={m.ts} tag="report" />
      <div className="bubble">
        <p>{o.summary}</p>
        {o.actions_taken.length > 0 && <ul className="done-list">{o.actions_taken.map((x, i) => <li key={i}>{x}</li>)}</ul>}
        {o.open_questions.length > 0 && <div className="why">open: {o.open_questions.join(' · ')}</div>}
        {o.facts.length > 0 && (
          <details className="facts">
            <summary>{o.facts.length} facts with sources</summary>
            <ul>{o.facts.map((f, i) => <li key={i}>{f.statement} <code>{f.source}</code></li>)}</ul>
          </details>
        )}
      </div>
    </div>
  )
}

function ShiftReport({ digest }: { digest: Digest }) {
  if (!digest.finished || digest.summaries.length === 0) return null
  return (
    <section className="shift">
      <div className="shift-head">Shift report · who did what on this ticket</div>
      <div className="shift-grid">
        {digest.summaries.map((s) => {
          const a = AGENTS[s.agent]
          return (
            <div key={s.agent} className="shift-card" style={{ ['--agent' as string]: a.color }}>
              <div className="shift-who"><span className="who-mono">{a.initials}</span>{a.label}</div>
              <p>{s.summary ? (s.summary.length > 260 ? `${s.summary.slice(0, 257)}…` : s.summary) : 'Joined the run.'}</p>
              <div className="shift-tools">
                {Object.entries(s.tools).map(([tool, n]) => (
                  <span key={tool} className="tool-count">{TOOL_LABELS[tool] ?? tool}{n > 1 ? ` ×${n}` : ''}</span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function ActionCard({ r, onApprove, onDeny, busy }: { r: PaymentRequest; onApprove: () => void; onDeny: () => void; busy: boolean }) {
  const what = r.kind === 'invoice' ? `invoice ${r.ref_id}` : `rent · lease ${r.ref_id}`
  if (r.status !== 'pending_approval') {
    const label = { approved: 'Paid', denied: 'Denied', rejected_insufficient_cash: 'Rejected — not enough cash' }[r.status]
    return (
      <div className={`receipt receipt-${r.status}`}>
        <b>{label}</b> {money(r.amount)} → {r.payee} <span>({what}) · {r.decided_by} · {r.decided_at}</span>
      </div>
    )
  }
  return (
    <div className="action">
      <div className="action-flag">Action needed</div>
      <div className="action-body">
        <div className="action-title">Pay <b>{r.payee}</b> <span className="amt">{money(r.amount)}</span></div>
        <div className="action-sub">{what} · requested by {AGENTS[r.requested_by as AgentName]?.label ?? r.requested_by} on {r.requested_on}</div>
        {r.reason && <div className="action-why">“{r.reason}”</div>}
      </div>
      <div className="action-btns">
        <button className="btn btn-approve" disabled={busy} onClick={onApprove}>{busy ? 'Paying…' : 'Approve & pay'}</button>
        <button className="btn btn-ghost" disabled={busy} onClick={onDeny}>Deny</button>
      </div>
    </div>
  )
}

export function Channel(p: Props) {
  const { ticket, digest, live } = p
  const scroller = useRef<HTMLDivElement>(null)
  const thinking = (Object.entries(digest.desks) as [AgentName, Digest['desks'][AgentName]][])
    .filter(([, d]) => live && d.state === 'thinking')
    .map(([n]) => n)

  useEffect(() => {
    const el = scroller.current
    if (el && live) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [digest.messages.length, live, thinking.length])

  const pending = p.requests.filter((r) => r.status === 'pending_approval')
  const decided = p.requests.filter((r) => r.status !== 'pending_approval')
  const status = ticket.running ? 'in_progress' : ticket.status

  return (
    <section className="channel-view" aria-label={`Ticket ${ticket.id}`}>
      <div className="channel-header">
        <div>
          <h1><span className="hash">#</span>ticket-{ticket.id} <span className="subject">· {ticket.subject}</span></h1>
          <div className="channel-brief">
            <span>{ticket.requester}</span>
            {ticket.sku && <span>{ticket.sku}{ticket.size ? ` · ${ticket.size}` : ''}{ticket.qty ? ` · qty ${ticket.qty}` : ''}</span>}
            {ticket.notes && <span className="quote">“{ticket.notes}”</span>}
          </div>
        </div>
        <div className="channel-actions">
          <span className={`pill pill-${status}`}>{live ? <span className="pulse" /> : null}{{
            open: 'Open', in_progress: 'Team working', waiting_on_human: 'Needs you', resolved: 'Resolved',
          }[status]}</span>
          <button className="btn btn-run" disabled={!p.canRun} onClick={p.onRun} title={p.runBlockedReason ?? ''}>
            {live ? 'Team is working…' : ticket.last_run ? 'Run the team again' : 'Hand to the team ▸'}
          </button>
        </div>
        {ticket.state === 'resolved' && <div className={`stamp ${p.celebrate ? 'stamp-in' : ''}`}>Resolved</div>}
        {p.celebrate && (
          <div className="confetti" aria-hidden>
            {Array.from({ length: 28 }, (_, i) => <i key={i} style={{ ['--i' as string]: i }} />)}
          </div>
        )}
      </div>

      <div className="feed" ref={scroller}>
        {digest.messages.length === 0 && !live && (
          <div className="empty">
            <div className="empty-art" aria-hidden>☕</div>
            <p>Nobody has picked this ticket up yet.</p>
            <p className="muted">Hand it to the team: the Boss reads it first and pulls in only the desks it needs.</p>
          </div>
        )}
        {digest.messages.map((m) => <MessageView key={m.id} m={m} ticketId={ticket.id} />)}
        {thinking.map((n) => (
          <div key={n} className="msg msg-typing" style={{ ['--agent' as string]: AGENTS[n].color }}>
            <span className="who-mono">{AGENTS[n].initials}</span>
            <span className="typing"><i /><i /><i /></span>
            <span className="muted">{AGENTS[n].label} is thinking…</span>
          </div>
        ))}
        <ShiftReport digest={digest} />
        {decided.length > 0 && <div className="receipts">{decided.map((r) => (
          <ActionCard key={r.id} r={r} busy={false} onApprove={() => {}} onDeny={() => {}} />
        ))}</div>}
      </div>

      {pending.length > 0 && (
        <div className="actions-dock">
          {pending.map((r) => (
            <ActionCard key={r.id} r={r} busy={p.busyRequest === r.id} onApprove={() => p.onApprove(r)} onDeny={() => p.onDeny(r)} />
          ))}
        </div>
      )}
    </section>
  )
}
