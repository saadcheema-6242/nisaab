/**
 * The few chart shapes the progress page needs, drawn as plain SVG.
 *
 * No chart library: these are three simple shapes, and a dependency that
 * ships a whole plotting engine to draw a row of bars is not worth the bundle
 * a student on a phone has to download first.
 *
 * Every chart here states a number as text as well as drawing it. A bar is
 * how you see at a glance which subject is behind; the figure beside it is how
 * you know by how much, and it is also what a screen reader gets.
 */

import { cn } from '@/lib/utils'

export const percent = (value?: number | null) =>
  `${Math.round((value ?? 0) * 100)}%`

/** How a mastery figure is coloured, from behind to secure. */
export const masteryTone = (value?: number | null) => {
  if (value === null || value === undefined) return 'bg-muted-foreground/25'
  if (value < 0.4) return 'bg-rose-500'
  if (value < 0.7) return 'bg-amber-500'
  return 'bg-emerald-500'
}

export type Bar = {
  label: string
  /** 0..1, or null when there is nothing measured yet */
  value: number | null
  /** Shown at the end of the row instead of the percentage, when given */
  note?: string
}

/**
 * A row of horizontal bars, which is the right shape whenever the labels are
 * words. Vertical bars would turn "Electricity and Magnetism" on its side.
 */
export const BarRows = ({
  bars,
  empty = 'Nothing practised yet',
}: {
  bars: ReadonlyArray<Bar>
  empty?: string
}) => {
  if (bars.length === 0)
    return <p className="text-sm text-muted-foreground">{empty}</p>

  return (
    <ul className="space-y-2.5">
      {bars.map((bar) => (
        <li key={bar.label} className="space-y-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate">{bar.label}</span>
            <span
              className={cn(
                'shrink-0 tabular-nums',
                bar.value === null
                  ? 'text-muted-foreground'
                  : 'font-medium',
              )}
            >
              {bar.note ?? (bar.value === null ? 'not practised' : percent(bar.value))}
            </span>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full bg-muted"
            role="img"
            aria-label={`${bar.label}: ${bar.note ?? (bar.value === null ? 'not practised' : percent(bar.value))}`}
          >
            <div
              className={cn('h-full rounded-full transition-all', masteryTone(bar.value))}
              style={{ width: `${Math.round((bar.value ?? 0) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

/**
 * How much of the syllabus has been touched at all, against how much there is.
 *
 * Deliberately separate from mastery, because they answer different questions
 * and mixing them flatters a student: scoring well on the four outcomes you
 * have tried is not the same as being ready for the paper.
 */
export const CoverageBar = ({
  practised,
  total,
}: {
  practised: number
  total: number
}) => {
  const share = total > 0 ? practised / total : 0
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-muted-foreground">Syllabus covered</span>
        <span className="tabular-nums font-medium">
          {practised} of {total} outcomes
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={`${practised} of ${total} outcomes practised`}
      >
        <div
          className="h-full rounded-full bg-sky-500 transition-all"
          style={{ width: `${Math.round(share * 100)}%` }}
        />
      </div>
    </div>
  )
}

/**
 * A ring showing one figure out of a hundred, for a predicted grade.
 *
 * Drawn with a stroke-dasharray on a circle, which is the whole trick: the
 * circumference is known, so the arc length is the percentage of it.
 */
export const Dial = ({
  value,
  caption,
  sub,
}: {
  /** 0..100 */
  value: number
  caption: string
  sub?: string
}) => {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const filled = (Math.max(0, Math.min(100, value)) / 100) * circumference
  const tone =
    value < 40 ? 'stroke-rose-500' : value < 70 ? 'stroke-amber-500' : 'stroke-emerald-500'

  return (
    <div className="flex items-center gap-4">
      <svg
        viewBox="0 0 100 100"
        className="size-24 shrink-0 -rotate-90"
        role="img"
        aria-label={`${caption}: ${value} percent`}
      >
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          strokeWidth="8"
          className="stroke-muted"
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
          className={cn('transition-all', tone)}
        />
      </svg>
      <div className="min-w-0">
        <div className="text-2xl font-semibold tabular-nums">{caption}</div>
        {sub && <p className="text-sm text-muted-foreground">{sub}</p>}
      </div>
    </div>
  )
}
