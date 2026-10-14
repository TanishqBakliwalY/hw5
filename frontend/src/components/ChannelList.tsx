import type { Ticket } from '../types'

const STATUS_LABEL: Record<Ticket['status'], string> = {
  open: 'Open',
  in_progress: 'Team working',
  waiting_on_human: 'Needs you',
  resolved: 'Resolved',
}

const KIND_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

export function ChannelList({
  tickets, selected, onSelect,
}: { tickets: Ticket[]; selected: number | null; onSelect: (id: number) => void }) {
  return (
    <nav className="channels" aria-label="Tickets">
      <div className="channels-head">Tickets</div>
      {tickets.map((t) => {
        const status = t.running ? 'in_progress' : t.status
        return (
          <button
            key={t.id}
            className={`channel ${selected === t.id ? 'channel-on' : ''} channel-${status}`}
            onClick={() => onSelect(t.id)}
            aria-current={selected === t.id}
          >
            <div className="channel-top">
              <span className="channel-hash">#</span>
              <span className="channel-id">ticket-{t.id}</span>
              {t.pending_approvals > 0 && <span className="badge" title="Payments waiting for you">{t.pending_approvals}</span>}
              {t.state === 'resolved' && <span className="check" aria-label="resolved">✓</span>}
            </div>
            <div className="channel-subject">{t.subject}</div>
            <div className="channel-meta">
              <span>{KIND_LABEL[t.type] ?? t.type}</span>
              <span className={`pill pill-${status}`}>
                {t.running ? <span className="pulse" /> : null}
                {STATUS_LABEL[status]}
              </span>
            </div>
            <div className="channel-from">from {t.requester}</div>
          </button>
        )
      })}
    </nav>
  )
}
