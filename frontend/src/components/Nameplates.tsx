import type { AgentName } from '../types'
import { AGENTS, AGENT_ORDER, TOOL_LABELS } from '../lib/agents'
import type { AgentDesk } from '../lib/feed'

function statusLine(d: AgentDesk): string {
  switch (d.state) {
    case 'thinking': return 'thinking'
    case 'tool': return `using ${TOOL_LABELS[d.detail ?? ''] ?? d.detail}`
    case 'waiting': return `waiting on ${AGENTS[d.detail as AgentName]?.label ?? 'a teammate'}`
    case 'done': return 'done'
    case 'error': return 'hit a problem'
    default: return d.joined ? 'idle' : 'at desk'
  }
}

export function Nameplates({ desks, live }: { desks: Record<AgentName, AgentDesk>; live: boolean }) {
  return (
    <div className="plates" role="list" aria-label="Agent desks">
      {AGENT_ORDER.map((name) => {
        const a = AGENTS[name]
        const d = desks[name]
        const active = live && (d.state === 'thinking' || d.state === 'tool' || d.state === 'waiting')
        return (
          <div
            key={name}
            role="listitem"
            className={`plate plate-${d.state} ${active ? 'plate-active' : ''} ${d.joined ? 'plate-joined' : ''}`}
            style={{ ['--agent' as string]: a.color }}
          >
            <div className="plate-mono">{a.initials}</div>
            <div className="plate-text">
              <div className="plate-name">{a.label}</div>
              <div className="plate-title">{a.title}</div>
              <div className="plate-status">
                {active && d.state === 'thinking' ? (
                  <span className="typing" aria-label="thinking"><i /><i /><i /></span>
                ) : null}
                {statusLine(d)}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
