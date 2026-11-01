import { Badge } from '@/components/ui/badge'
import { MathText } from '@/components/math-text'
import type { StudyPlanItem } from '@/integrations/api/client'

const ACTION_LABELS: Record<string, string> = {
  read: 'Read',
  flashcards: 'Flashcards',
  quiz: 'Quiz',
  srq: 'Short question',
  paper: 'Paper',
}

/** How long a sitting takes, written the way a person would say it. */
export const spellMinutes = (minutes: number) => {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

/**
 * A study plan's steps, grouped by day.
 *
 * Each step names the FBISE outcome it practises and what counts as done, so
 * the plan is something a student can work through rather than read once. The
 * same component serves the chat and the study plan page, because a plan that
 * looked different in the two places would read as two different plans.
 */
export const StudyPlanSteps = ({
  items,
}: {
  items: ReadonlyArray<StudyPlanItem>
}) => {
  const days = [...new Set(items.map((item) => item.day))].sort((a, b) => a - b)

  return (
    <ol className="space-y-3">
      {days.map((day) => (
        <li key={day} className="space-y-1.5">
          <div className="text-xs font-semibold text-muted-foreground">
            Day {day}
          </div>
          <ul className="space-y-1.5">
            {items
              .filter((item) => item.day === day)
              .map((item, index) => (
                <li
                  key={`${day}-${index}`}
                  className="rounded-lg border bg-background/60 p-2.5"
                >
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                    <Badge variant="outline" className="font-mono">
                      {item.slo_code}
                    </Badge>
                    <Badge variant="secondary">
                      {ACTION_LABELS[item.action] ?? item.action}
                    </Badge>
                    <span className="text-muted-foreground">
                      {spellMinutes(item.minutes)}
                    </span>
                    {/* Why this step is in the plan at all */}
                    {item.standing === 'struggling' && (
                      <Badge variant="destructive">Needs work</Badge>
                    )}
                    {item.standing === 'unknown' && (
                      <Badge variant="outline">Not practised yet</Badge>
                    )}
                  </div>
                  <MathText className="mt-1 text-sm leading-relaxed">
                    {item.title}
                  </MathText>
                  {item.target && (
                    <div className="mt-1 text-xs font-medium text-emerald-700 dark:text-emerald-400">
                      {item.target}
                    </div>
                  )}
                </li>
              ))}
          </ul>
        </li>
      ))}
    </ol>
  )
}
