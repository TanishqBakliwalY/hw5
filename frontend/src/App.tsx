import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from './api'
import type { CashResponse, FeedEvent, Health, PaymentRequest, TicketsResponse } from './types'
import { Briefing } from './components/Briefing'
import { Nameplates } from './components/Nameplates'
import { ChannelList } from './components/ChannelList'
import { Channel } from './components/Channel'
import { SidePanel } from './components/SidePanel'
import { digest as buildDigest } from './lib/feed'
import { chime, unlockAudio } from './lib/ui'
import { money } from './lib/agents'

interface Toast { id: number; text: string; tone: 'ok' | 'warn' | 'err' }

const AGENT_NAMES = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export default function App() {
  const [tickets, setTickets] = useState<TicketsResponse | null>(null)
  const [cash, setCash] = useState<CashResponse | null>(null)
  const [requests, setRequests] = useState<PaymentRequest[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [online, setOnline] = useState(true)
  // ?ticket=101 opens that channel directly (handy for links and screenshots)
  const [selected, setSelected] = useState<number | null>(() => Number(new URLSearchParams(location.search).get('ticket')) || null)
  const [runOverride, setRunOverride] = useState<{ ticket: number; run: string } | null>(null)
  const [events, setEvents] = useState<FeedEvent[]>([])
  const [busyRequest, setBusyRequest] = useState<number | null>(null)
  const [celebrate, setCelebrate] = useState<number | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const approverRef = useRef<HTMLInputElement>(null)
  const cursor = useRef<number | undefined>(undefined)
  const loadedRun = useRef<string | null>(null)
  const prevStatus = useRef<Record<number, string>>({})
  const prevPending = useRef<number | null>(null)

  const toast = useCallback((text: string, tone: Toast['tone'] = 'ok') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, text, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200)
  }, [])

  // ------------------------------------------------------------------ shop state polling
  const refresh = useCallback(async () => {
    try {
      const [t, c, p] = await Promise.all([api.tickets(), api.cash(), api.payments()])
      setTickets(t)
      setCash(c)
      setRequests(p.requests)
      setOnline(true)
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    api.health().then(setHealth).catch(() => setOnline(false))
  }, [refresh])

  const anyRunning = !!tickets?.current_run
  useEffect(() => {
    const t = setInterval(refresh, anyRunning ? 1500 : 5000)
    return () => clearInterval(t)
  }, [refresh, anyRunning])

  useEffect(() => {
    if (selected === null && tickets?.tickets.length) setSelected(tickets.tickets[0].id)
  }, [tickets, selected])

  const ticket = tickets?.tickets.find((t) => t.id === selected) ?? null
  const runId = runOverride && runOverride.ticket === selected ? runOverride.run : ticket?.last_run?.run_id ?? null
  const live = !!ticket && !!runId && tickets?.current_run === runId

  // ------------------------------------------------------------------ resolved celebration
  useEffect(() => {
    if (!tickets) return
    for (const t of tickets.tickets) {
      const before = prevStatus.current[t.id]
      if (before && before !== 'resolved' && t.status === 'resolved') {
        setCelebrate(t.id)
        toast(`Ticket ${t.id} resolved — nice work.`)
        setTimeout(() => setCelebrate((c) => (c === t.id ? null : c)), 3200)
      }
      prevStatus.current[t.id] = t.status
    }
  }, [tickets, toast])

  // ------------------------------------------------------------------ approval alerts
  const pendingCount = requests.filter((r) => r.status === 'pending_approval').length
  useEffect(() => {
    if (!tickets) return // don't chime for requests that were already waiting when the page opened
    document.title = pendingCount > 0 ? `(${pendingCount}) Needs you · Campus Customs Desk` : 'Campus Customs Desk'
    if (prevPending.current !== null && pendingCount > prevPending.current) {
      chime()
      const newest = requests.filter((r) => r.status === 'pending_approval').at(-1)
      if (newest) toast(`${newest.payee} · ${money(newest.amount)} needs your approval`, 'warn')
    }
    prevPending.current = pendingCount
  }, [pendingCount, requests, toast, tickets])

  // ------------------------------------------------------------------ event feed for the open channel
  useEffect(() => {
    if (!runId) {
      setEvents([])
      loadedRun.current = null
      return
    }
    let stop = false
    const load = async () => {
      try {
        const fresh = loadedRun.current !== runId
        const res = await api.events({ run_id: runId, after: fresh ? undefined : cursor.current })
        if (stop) return
        cursor.current = res.next_after
        if (fresh) {
          loadedRun.current = runId
          setEvents(res.events)
        } else if (res.events.length) {
          setEvents((ev) => [...ev, ...res.events])
        }
      } catch {
        /* backend hiccup; next tick retries */
      }
    }
    void load()
    if (!live) return () => { stop = true }
    const t = setInterval(load, 1200)
    return () => {
      // when the run ends this effect re-runs with live=false and pulls the last events once
      stop = true
      clearInterval(t)
    }
  }, [runId, live])

  const digest = useMemo(() => buildDigest(events), [events])

  // ------------------------------------------------------------------ actions
  const run = async () => {
    if (!ticket) return
    unlockAudio()
    try {
      const r = await api.runTicket(ticket.id)
      setRunOverride({ ticket: ticket.id, run: r.run_id })
      loadedRun.current = null
      setEvents([])
      toast(`Ticket ${ticket.id} handed to the team.`)
      void refresh()
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Could not start the run.', 'err')
    }
  }

  const needName = () => {
    const name = approver.trim()
    if (name.length < 2 || AGENT_NAMES.includes(name.toLowerCase())) {
      toast('Type your name in “Approving as” first — only a person can approve money.', 'warn')
      approverRef.current?.focus()
      return null
    }
    return name
  }

  const approve = async (r: PaymentRequest) => {
    unlockAudio()
    const name = needName()
    if (!name) return
    setBusyRequest(r.id)
    try {
      const res = await api.approve(r.id, name)
      toast(`Paid ${res.payee} ${money(r.amount)} · checking ${money(res.balance_before)} → ${money(res.balance_after)}`)
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Approval failed.', 'err')
    } finally {
      setBusyRequest(null)
      void refresh()
    }
  }

  const deny = async (r: PaymentRequest) => {
    const name = needName()
    if (!name) return
    const reason = window.prompt(`Why deny paying ${r.payee} ${money(r.amount)}?`, '') ?? ''
    setBusyRequest(r.id)
    try {
      await api.deny(r.id, name, reason)
      toast(`Denied request #${r.id}. No money moved.`, 'warn')
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Deny failed.', 'err')
    } finally {
      setBusyRequest(null)
      void refresh()
    }
  }

  const setName = (n: string) => {
    setApprover(n)
    localStorage.setItem('cc-approver', n)
  }

  const ticketRequests = ticket?.payment_requests ?? []
  const runBlocked = !ticket ? 'Pick a ticket'
    : ticket.state === 'resolved' ? 'This ticket is resolved'
    : tickets?.current_run ? 'Another run is in progress'
    : null

  return (
    <div className="desk">
      <Briefing tickets={tickets} cash={cash} approver={approver} onApprover={setName} approverRef={approverRef} online={online} />
      <Nameplates desks={digest.desks} live={live} />
      <div className="floor">
        <ChannelList tickets={tickets?.tickets ?? []} selected={selected} onSelect={(id) => { setSelected(id); setRunOverride(null) }} />
        {ticket ? (
          <Channel
            ticket={ticket}
            digest={digest}
            live={live}
            canRun={!runBlocked}
            runBlockedReason={runBlocked}
            onRun={run}
            requests={ticketRequests}
            onApprove={approve}
            onDeny={deny}
            busyRequest={busyRequest}
            celebrate={celebrate === ticket.id}
          />
        ) : (
          <section className="channel-view empty">{online ? 'Loading tickets…' : 'Backend offline — start uvicorn on port 8000.'}</section>
        )}
        <SidePanel cash={cash} requests={requests} ticketId={selected} digest={digest} hasRun={!!runId} health={health} live={live} />
      </div>
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => <div key={t.id} className={`toast toast-${t.tone}`}>{t.text}</div>)}
      </div>
    </div>
  )
}
