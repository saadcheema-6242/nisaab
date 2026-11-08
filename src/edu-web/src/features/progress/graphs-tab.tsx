/**
 * The graphs half of the progress page.
 *
 * The overview tab answers "where am I". This one answers "am I getting
 * better, what kind of question am I losing marks on, and am I actually
 * turning up" - the three things a student cannot work out from a single
 * snapshot, and the three a teacher asks about first.
 *
 * It loads on its own, from its own endpoint, the first time the tab is
 * opened. Nobody pays for a query over every answer they have ever given
 * unless they ask to see it.
 */

import { Result, useAtomValue } from '@effect-atom/atom-react'
import { CalendarCheckIcon, FlameIcon, TrendingUpIcon } from 'lucide-react'
import { percent } from './charts'
import { ActivityCalendar, CognitiveBars, TrendLine } from './graph-charts'
import type { SubjectGraphs } from '@/data-acess/progress'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { progressGraphsAtom } from '@/data-acess/progress'
import { SubjectIcon } from '@/lib/subjects'

const Figure = ({
  icon: Icon,
  value,
  label,
}: {
  icon: typeof FlameIcon
  value: string | number
  label: string
}) => (
  <div className="flex items-center gap-3 rounded-lg border p-3">
    <Icon className="text-muted-foreground size-4 shrink-0" />
    <div>
      <p className="text-xl font-semibold tabular-nums">{value}</p>
      <p className="text-muted-foreground text-xs">{label}</p>
    </div>
  </div>
)

const SubjectGraphCard = ({ subject }: { subject: SubjectGraphs }) => (
  <Card>
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-base">
        <SubjectIcon code={subject.subject_code} className="size-4" />
        {subject.name}
        {subject.mastery !== null && (
          <Badge variant="secondary" className="ml-auto tabular-nums">
            {percent(subject.mastery)} now
          </Badge>
        )}
      </CardTitle>
    </CardHeader>
    <CardContent className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-medium">Mastery week by week</h3>
        <TrendLine points={subject.trend} label={subject.name} />
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Against what the paper asks for</h3>
        <CognitiveBars levels={subject.cognitive} />
        {subject.weakest_level && (
          <p className="rounded-md border border-amber-300 bg-amber-50 p-2.5 text-xs dark:border-amber-900 dark:bg-amber-950/40">
            About <strong>{subject.weakest_level.marks_at_stake} marks</strong>{' '}
            are going on {subject.weakest_level.name} questions. That is where
            revision pays back most in this subject.
          </p>
        )}
      </div>
    </CardContent>
  </Card>
)

export const GraphsTab = () => {
  const result = useAtomValue(progressGraphsAtom)

  if (Result.isFailure(result)) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="text-sm font-medium">The graphs could not be loaded</p>
          <p className="text-muted-foreground mt-1 text-sm">
            Your progress is safe. Try again in a moment.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!Result.isSuccess(result)) {
    return (
      <p className="text-muted-foreground p-6 text-sm">
        Working out your progress…
      </p>
    )
  }

  const { subjects, consistency, overall_trend } = result.value
  const everPractised = consistency.days_practised > 0

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">How you are going</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Figure
              icon={FlameIcon}
              value={consistency.current_streak}
              label={
                consistency.current_streak === 1
                  ? 'day in a row'
                  : 'days in a row'
              }
            />
            <Figure
              icon={TrendingUpIcon}
              value={consistency.longest_streak}
              label="best run"
            />
            <Figure
              icon={CalendarCheckIcon}
              value={consistency.days_practised}
              label="days practised"
            />
            <Figure
              icon={CalendarCheckIcon}
              value={consistency.answers_this_week}
              label="answers this week"
            />
          </div>

          {everPractised && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Every subject together</h3>
              <TrendLine points={overall_trend} label="All subjects" />
            </div>
          )}

          <div className="space-y-2">
            <h3 className="text-sm font-medium">When you practised</h3>
            <ActivityCalendar days={consistency.calendar} />
          </div>
        </CardContent>
      </Card>

      {subjects.map((subject) => (
        <SubjectGraphCard key={subject.project_id} subject={subject} />
      ))}
    </div>
  )
}
