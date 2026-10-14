import type { CashResponse, TicketsResponse } from '../types'
import { money } from '../lib/agents'
import { RollingMoney } from '../lib/ui'

interface Props {
  tickets: TicketsResponse | null
  cash: CashResponse | null
  approver: string
  onApprover: (name: string) => void
  approverRef: React.RefObject<HTMLInputElement | null>
  online: boolean
}

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

function shopDay(iso?: string) {
  if (!iso) return '—'
  return new Date(`${iso}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

export function Briefing({ tickets, cash, approver, onApprover, approverRef, online }: Props) {
  const open = tickets?.tickets.filter((t) => t.state === 'open').length ?? 0
  const needs = tickets?.tickets.filter((t) => t.pending_approvals > 0).length ?? 0
  const resolved = tickets?.resolved_count ?? 0

  return (
    <header className="briefing">
      <div className="brand">
        <div className="logo" aria-hidden>
          <span>CC</span>
        </div>
        <div>
          <div className="brand-name">Campus Customs <span>· Desk</span></div>
          <div className="brand-sub">Chapel Street · the team works, you decide</div>
        </div>
      </div>

      <div className="hello">
        <div className="hello-line">
          {greeting()}{approver ? `, ${approver.split(' ')[0]}` : ''}.
        </div>
        <div className="hello-date">
          At the shop it’s <b>{shopDay(tickets?.date_today)}</b>
          <span className={`dot ${online ? 'on' : 'off'}`} title={online ? 'Backend connected' : 'Backend offline'} />
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <div className="stat-k">Open tickets</div>
          <div className="stat-v">{open}</div>
        </div>
        <div className={`stat ${cash && cash.pending_requests > 0 ? 'stat-alert' : ''}`}>
          <div className="stat-k">Waiting on you</div>
          <div className="stat-v">
            {cash ? money(cash.pending_total) : '—'}
            <small>{cash?.pending_requests ?? 0} pay · {needs} ticket{needs === 1 ? '' : 's'}</small>
          </div>
        </div>
        <div className="stat stat-cash">
          <div className="stat-k">Checking</div>
          <div className="stat-v">{cash ? <RollingMoney value={cash.balance} /> : '—'}</div>
        </div>
        <div className="stat">
          <div className="stat-k">Resolved</div>
          <div className="stat-v">{resolved}<small>of {tickets?.tickets.length ?? 0}</small></div>
        </div>
      </div>

      <label className="approver">
        <span>Approving as</span>
        <input
          ref={approverRef}
          value={approver}
          placeholder="your name"
          onChange={(e) => onApprover(e.target.value)}
          aria-label="Your name for approvals"
        />
      </label>
    </header>
  )
}
