// Turns the audit-trail feed for one run into chat messages, nameplate states and summaries.
import type { AgentName, AgentReport, BossReport, FeedEvent } from '../types'
import { AGENT_ORDER } from './agents'

export interface Chip { key: string; tool: string; done: boolean; ms?: number }

export type Message =
  | { kind: 'system'; id: string; ts: string; text: string; tone: 'start' | 'end' | 'fail' | 'info' }
  | { kind: 'handoff'; id: string; ts: string; from: AgentName; to: AgentName; task: string; reason?: string; depth: number }
  | { kind: 'work'; id: string; ts: string; agent: AgentName; depth: number; chips: Chip[] }
  | { kind: 'say'; id: string; ts: string; agent: AgentName; depth: number; text: string }
  | { kind: 'report'; id: string; ts: string; agent: AgentName; depth: number; output: AgentReport }
  | { kind: 'final'; id: string; ts: string; output: BossReport }

export type DeskState = 'idle' | 'thinking' | 'tool' | 'waiting' | 'done' | 'error'
export interface AgentDesk { state: DeskState; detail?: string; joined: boolean }

export interface AgentSummary {
  agent: AgentName
  summary: string | null
  tools: Record<string, number>
}

export interface RunUsageTotals { requests: number; toolCalls: number; inputTokens: number; outputTokens: number }

export interface Digest {
  messages: Message[]
  desks: Record<AgentName, AgentDesk>
  summaries: AgentSummary[]
  delegations: [AgentName, AgentName][]
  toolsByAgent: Partial<Record<AgentName, Set<string>>>
  usage: RunUsageTotals
  finished: boolean
  failed: boolean
  startedAt?: string
  endedAt?: string
}

const emptyDesks = (): Record<AgentName, AgentDesk> =>
  Object.fromEntries(AGENT_ORDER.map((a) => [a, { state: 'idle', joined: false }])) as Record<AgentName, AgentDesk>

export function digest(events: FeedEvent[]): Digest {
  const messages: Message[] = []
  const desks = emptyDesks()
  const summaries = new Map<AgentName, AgentSummary>()
  const delegations: [AgentName, AgentName][] = []
  const toolsByAgent: Partial<Record<AgentName, Set<string>>> = {}
  const usage: RunUsageTotals = { requests: 0, toolCalls: 0, inputTokens: 0, outputTokens: 0 }
  const chipIndex = new Map<string, Chip>()
  let finished = false
  let failed = false
  let startedAt: string | undefined
  let endedAt: string | undefined

  const summaryFor = (a: AgentName) => {
    if (!summaries.has(a)) summaries.set(a, { agent: a, summary: null, tools: {} })
    return summaries.get(a)!
  }
  const countTool = (a: AgentName, tool: string) => {
    const s = summaryFor(a)
    s.tools[tool] = (s.tools[tool] ?? 0) + 1
    ;(toolsByAgent[a] ??= new Set()).add(tool)
  }

  for (const e of events) {
    const a = e.agent
    const depth = e.depth ?? 0
    const id = String(e.id)

    switch (e.event) {
      case 'run_start':
        startedAt = e.ts
        messages.push({ kind: 'system', id, ts: e.ts, tone: 'start', text: 'Ticket handed to the team — the Boss is reading it.' })
        break
      case 'run_end':
        finished = true
        endedAt = e.ts
        messages.push({ kind: 'system', id, ts: e.ts, tone: 'end', text: 'The team has finished this ticket.' })
        break
      case 'run_failed':
        finished = true
        failed = true
        endedAt = e.ts
        messages.push({ kind: 'system', id, ts: e.ts, tone: 'fail', text: `Run stopped: ${e.text.replace(/^run failed: /, '')}` })
        break
      case 'agent_start':
        if (a) desks[a] = { state: 'thinking', joined: true }
        if (a) summaryFor(a)
        break
      case 'model_request':
        if (a && desks[a].state !== 'waiting') desks[a] = { ...desks[a], state: 'thinking', detail: undefined }
        break
      case 'model_response': {
        if (!a) break
        usage.requests += 1
        usage.inputTokens += e.usage?.input_tokens ?? 0
        usage.outputTokens += e.usage?.output_tokens ?? 0
        if (e.said) messages.push({ kind: 'say', id, ts: e.ts, agent: a, depth, text: e.said })
        break
      }
      case 'tool_call': {
        if (!a || !e.meta.tool) break
        usage.toolCalls += 1
        countTool(a, e.meta.tool)
        desks[a] = { ...desks[a], state: 'tool', detail: e.meta.tool }
        const chip: Chip = { key: e.meta.tool_call_id ?? id, tool: e.meta.tool, done: false }
        chipIndex.set(chip.key, chip)
        const last = messages[messages.length - 1]
        if (last && last.kind === 'work' && last.agent === a) last.chips.push(chip)
        else messages.push({ kind: 'work', id, ts: e.ts, agent: a, depth, chips: [chip] })
        break
      }
      case 'tool_result': {
        const chip = chipIndex.get(e.meta.tool_call_id ?? '')
        if (chip) {
          chip.done = true
          chip.ms = e.meta.ms
        }
        if (a && desks[a].state === 'tool') desks[a] = { ...desks[a], state: 'thinking', detail: undefined }
        break
      }
      case 'delegation_start':
        if (!a || !e.meta.to_agent) break
        usage.toolCalls += 1
        countTool(a, 'delegate')
        delegations.push([a, e.meta.to_agent])
        desks[a] = { ...desks[a], state: 'waiting', detail: e.meta.to_agent }
        messages.push({
          kind: 'handoff', id, ts: e.ts, from: a, to: e.meta.to_agent,
          task: e.meta.task ?? '', reason: e.meta.reason, depth,
        })
        break
      case 'delegation_result':
        if (a) {
          // other hand-offs from the same agent may still be out (parallel delegations)
          const stillOut = Object.entries(desks).some(([n, d]) => n !== a && d.joined && d.state !== 'done' && d.state !== 'idle')
          desks[a] = { ...desks[a], state: stillOut ? 'waiting' : 'thinking', detail: stillOut ? desks[a].detail : undefined }
        }
        break
      case 'delegation_refused':
        messages.push({ kind: 'system', id, ts: e.ts, tone: 'info', text: e.text })
        break
      case 'agent_end': {
        if (!a) break
        desks[a] = { ...desks[a], state: 'done', detail: undefined }
        const out = e.meta.output
        if (!out) break
        if ('tickets' in out) {
          summaryFor(a).summary = out.tickets.map((t) => t.summary).join(' ')
          messages.push({ kind: 'final', id, ts: e.ts, output: out })
        } else {
          summaryFor(a).summary = out.summary
          messages.push({ kind: 'report', id, ts: e.ts, agent: a, depth, output: out })
        }
        break
      }
      case 'agent_error':
        if (a) desks[a] = { ...desks[a], state: 'error', detail: e.text }
        break
    }
  }

  if (finished) {
    for (const n of AGENT_ORDER) if (desks[n].joined && desks[n].state !== 'error') desks[n] = { ...desks[n], state: 'done' }
  }

  return {
    messages,
    desks,
    summaries: AGENT_ORDER.filter((n) => summaries.has(n)).map((n) => summaries.get(n)!),
    delegations,
    toolsByAgent,
    usage,
    finished,
    failed,
    startedAt,
    endedAt,
  }
}
