import { useEffect, useRef, useState } from 'react'
import { money } from './agents'

/** Money that rolls to its new value, so a payment visibly drains the balance. */
export function RollingMoney({ value, className }: { value: number; className?: string }) {
  const [shown, setShown] = useState(value)
  const [dir, setDir] = useState<'up' | 'down' | null>(null)
  const from = useRef(value)

  useEffect(() => {
    const start = from.current
    if (start === value) return
    setDir(value < start ? 'down' : 'up')
    const t0 = performance.now()
    const dur = 1100
    let raf = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / dur)
      const ease = 1 - Math.pow(1 - k, 3)
      setShown(start + (value - start) * ease)
      if (k < 1) raf = requestAnimationFrame(tick)
      else {
        from.current = value
        setTimeout(() => setDir(null), 900)
      }
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])

  return <span className={`${className ?? ''} rolling ${dir ? `rolling-${dir}` : ''}`}>{money(shown)}</span>
}

/** Tiny balance-over-time line. */
export function Sparkline({ points, width = 220, height = 46 }: { points: number[]; width?: number; height?: number }) {
  if (points.length < 2) {
    return (
      <svg width={width} height={height} className="spark" aria-hidden>
        <line x1="0" x2={width} y1={height / 2} y2={height / 2} className="spark-flat" />
      </svg>
    )
  }
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  const xy = points.map((p, i) => [
    (i / (points.length - 1)) * (width - 8) + 4,
    height - 6 - ((p - min) / span) * (height - 12),
  ])
  const d = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${d} L${xy[xy.length - 1][0]},${height} L${xy[0][0]},${height} Z`
  const [lx, ly] = xy[xy.length - 1]
  return (
    <svg width={width} height={height} className="spark" aria-label="Checking balance over time">
      <path d={area} className="spark-area" />
      <path d={d} className="spark-line" />
      <circle cx={lx} cy={ly} r="3.5" className="spark-dot" />
    </svg>
  )
}

let audio: AudioContext | null = null

/** Unlock audio on the first user gesture (browsers block sound before that). */
export function unlockAudio() {
  if (!audio) audio = new AudioContext()
  if (audio.state === 'suspended') void audio.resume()
}

/** Soft two-note chime for "an agent needs your approval". */
export function chime() {
  if (!audio || audio.state !== 'running') return
  const now = audio.currentTime
  ;[659.25, 987.77].forEach((f, i) => {
    const o = audio!.createOscillator()
    const g = audio!.createGain()
    o.type = 'sine'
    o.frequency.value = f
    g.gain.setValueAtTime(0, now + i * 0.16)
    g.gain.linearRampToValueAtTime(0.12, now + i * 0.16 + 0.02)
    g.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.16 + 0.6)
    o.connect(g).connect(audio!.destination)
    o.start(now + i * 0.16)
    o.stop(now + i * 0.16 + 0.65)
  })
}

export const clock = (ts?: string) =>
  ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''
