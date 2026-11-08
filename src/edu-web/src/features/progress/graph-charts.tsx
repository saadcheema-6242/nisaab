/**
 * The charts the graphs tab needs, drawn as plain SVG.
 *
 * Still no chart library. A line, a grouped bar and a calendar are a few
 * dozen lines of geometry each, and a plotting engine is a large download for
 * a student on a phone before they have seen anything.
 *
 * Every chart states its numbers as text as well as drawing them: the shape
 * is how you see the direction at a glance, the figures are how you know by
 * how much, and they are what a screen reader gets.
 */

import { masteryTone, percent } from './charts'
import { cn } from '@/lib/utils'

export type TrendPoint = {
  week_start: string
  mastery: number | null
  attempts: number
}

/** A date as a student would say it: "9 Nov". */
const shortDate = (iso: string) => {
  const when = new Date(iso + 'T00:00:00')
  return when.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

/**
 * Mastery week by week.
 *
 * Drawn with a viewBox and no fixed width so it fills whatever it is given,
 * which on a phone is about three hundred pixels and on a laptop three times
 * that. Stroke widths are set in the same units, so the line does not thin
 * out as the card grows.
 */
export const TrendLine = ({
  points,
  label,
}: {
  points: Array<TrendPoint>
  label: string
}) => {
  const scored = points.filter((p) => p.mastery !== null)
  if (scored.length < 2) {
    return (
      <p className="text-muted-foreground py-6 text-center text-sm">
        {scored.length === 0
          ? 'No practice recorded yet. Answer a few questions and your progress will show here.'
          : 'One week of practice so far. The line appears once there are two.'}
      </p>
    )
  }

  const W = 320
  const H = 110
  const PAD_L = 28
  const PAD_B = 18
  const PAD_T = 8

  const step = (W - PAD_L - 6) / Math.max(1, points.length - 1)
  const y = (value: number) => PAD_T + (1 - value) * (H - PAD_T - PAD_B)
  const x = (index: number) => PAD_L + index * step

  // Only the weeks that have a value are joined. A null at the start means
  // the student had not practised yet, and drawing it as zero would show a
  // climb out of nothing that never happened.
  const drawn = points
    .map((p, i) => ({ ...p, i }))
    .filter((p) => p.mastery !== null) as Array<TrendPoint & { i: number; mastery: number }>

  const line = drawn
    .map((p, n) => `${n === 0 ? 'M' : 'L'} ${x(p.i).toFixed(1)} ${y(p.mastery).toFixed(1)}`)
    .join(' ')
  const area =
    `${line} L ${x(drawn[drawn.length - 1].i).toFixed(1)} ${H - PAD_B} ` +
    `L ${x(drawn[0].i).toFixed(1)} ${H - PAD_B} Z`

  const first = drawn[0]
  const last = drawn[drawn.length - 1]
  const change = Math.round((last.mastery - first.mastery) * 100)

  return (
    <div className="space-y-1">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-32 w-full"
        role="img"
        aria-label={`${label}: mastery went from ${percent(first.mastery)} on ${shortDate(
          first.week_start,
        )} to ${percent(last.mastery)} on ${shortDate(last.week_start)}`}
      >
        {/* Quarter lines, so a reader can judge a height without a ruler */}
        {[0, 0.25, 0.5, 0.75, 1].map((at) => (
          <g key={at}>
            <line
              x1={PAD_L}
              x2={W - 2}
              y1={y(at)}
              y2={y(at)}
              className="stroke-border"
              strokeWidth={0.5}
            />
            {(at === 0 || at === 0.5 || at === 1) && (
              <text
                x={PAD_L - 4}
                y={y(at) + 3}
                textAnchor="end"
                className="fill-muted-foreground"
                style={{ fontSize: 7 }}
              >
                {at * 100}
              </text>
            )}
          </g>
        ))}

        <path d={area} className="fill-primary/10" />
        <path
          d={line}
          fill="none"
          className="stroke-primary"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {drawn.map((p) => (
          <circle
            key={p.week_start}
            cx={x(p.i)}
            cy={y(p.mastery)}
            r={1.8}
            className="fill-primary"
          />
        ))}

        <text
          x={PAD_L}
          y={H - 5}
          className="fill-muted-foreground"
          style={{ fontSize: 7 }}
        >
          {shortDate(points[0].week_start)}
        </text>
        <text
          x={W - 2}
          y={H - 5}
          textAnchor="end"
          className="fill-muted-foreground"
          style={{ fontSize: 7 }}
        >
          {shortDate(points[points.length - 1].week_start)}
        </text>
      </svg>

      <p className="text-muted-foreground text-xs">
        {change > 0
          ? `Up ${change} points since ${shortDate(first.week_start)}`
          : change < 0
            ? `Down ${Math.abs(change)} points since ${shortDate(first.week_start)}`
            : `Steady since ${shortDate(first.week_start)}`}
        {' · '}
        {last.attempts} answers recorded
      </p>
    </div>
  )
}

export type CognitiveLevel = {
  level: string
  name: string
  paper_weight: number
  mastery: number | null
  examined_count: number
  practised_count: number
}

/**
 * Mastery at each FBISE cognitive level, against what the paper weights it.
 *
 * The weight is shown beside the score rather than instead of it, because
 * the pair is the whole point: 40% on Application and 40% on Understanding
 * are not the same problem, and only the weighting says which to revise.
 */
export const CognitiveBars = ({ levels }: { levels: Array<CognitiveLevel> }) => {
  const anyPractised = levels.some((l) => l.mastery !== null)
  if (!anyPractised) {
    return (
      <p className="text-muted-foreground py-4 text-sm">
        Nothing practised yet, so there is nothing to compare against the paper.
      </p>
    )
  }
  return (
    <ul className="space-y-2.5">
      {levels.map((level) => (
        <li key={level.level} className="space-y-1">
          <div className="flex items-baseline gap-2 text-sm">
            <span className="font-medium">{level.name}</span>
            <span className="text-muted-foreground text-xs">
              {level.paper_weight}% of the paper
            </span>
            <span className="ml-auto tabular-nums">
              {level.mastery === null ? '—' : percent(level.mastery)}
            </span>
          </div>
          <div
            className="bg-muted h-2 w-full overflow-hidden rounded-full"
            role="img"
            aria-label={`${level.name}: ${
              level.mastery === null ? 'not practised' : percent(level.mastery)
            }, worth ${level.paper_weight} percent of the paper`}
          >
            <div
              className={cn('h-full rounded-full', masteryTone(level.mastery))}
              style={{ width: `${Math.round((level.mastery ?? 0) * 100)}%` }}
            />
          </div>
          <p className="text-muted-foreground text-xs">
            {level.practised_count} of {level.examined_count} outcomes practised
          </p>
        </li>
      ))}
    </ul>
  )
}

export type ActivityDay = { day: string; answers: number }

/**
 * The last weeks of practice, one square per day.
 *
 * The empty squares are the point. A chart of only the days a student worked
 * is a trophy cabinet; the gaps are what tells them, without a word of
 * nagging, that last week went quiet.
 */
export const ActivityCalendar = ({ days }: { days: Array<ActivityDay> }) => {
  if (days.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        No practice recorded yet.
      </p>
    )
  }

  // Twelve weeks is about a term, and fits a phone without scrolling.
  const shown = days.slice(-84)
  const weeks: Array<Array<ActivityDay>> = []
  for (let i = 0; i < shown.length; i += 7) weeks.push(shown.slice(i, i + 7))

  const tone = (answers: number) => {
    if (answers === 0) return 'bg-muted'
    if (answers < 3) return 'bg-emerald-500/30'
    if (answers < 8) return 'bg-emerald-500/60'
    return 'bg-emerald-500'
  }

  const worked = shown.filter((d) => d.answers > 0).length

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1 overflow-x-auto pb-1">
        {weeks.map((week, i) => (
          <div key={i} className="flex flex-col gap-1">
            {week.map((day) => (
              <div
                key={day.day}
                title={`${day.day}: ${day.answers} ${
                  day.answers === 1 ? 'answer' : 'answers'
                }`}
                className={cn('size-2.5 shrink-0 rounded-sm', tone(day.answers))}
              />
            ))}
          </div>
        ))}
      </div>
      <p className="text-muted-foreground text-xs">
        {worked} of the last {shown.length} days practised
      </p>
    </div>
  )
}
