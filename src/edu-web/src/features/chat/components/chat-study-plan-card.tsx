import { Result, useAtomRefresh, useAtomValue } from '@effect-atom/atom-react'
import { CalendarDaysIcon, Loader2Icon } from 'lucide-react'
import { useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { latestStudyPlanRemoteAtom } from '@/data-acess/study-plan'
import { MathText } from '@/components/math-text'
import {
  StudyPlanSteps,
  spellMinutes,
} from '@/features/study-plan/components/study-plan-steps'


/**
 * A study plan the tutor made, shown in the chat.
 *
 * Read from the project's latest plan rather than carried in the tool's reply:
 * a plan is forty-odd steps, and putting all of them in the reply would mean
 * sending the whole thing back through the model on every later message.
 */
export const ChatStudyPlanCard = ({
  projectId,
  studyPlanId,
}: {
  projectId: string
  studyPlanId: string
}) => {
  const atom = latestStudyPlanRemoteAtom(projectId)
  const result = useAtomValue(atom)
  const refresh = useAtomRefresh(atom)

  // The plan was made during this turn, so anything already loaded predates it
  useEffect(() => {
    refresh()
  }, [studyPlanId, refresh])

  if (!Result.isSuccess(result)) {
    return (
      <div className="flex max-w-2xl items-center gap-2 rounded-xl border bg-card p-4 text-sm text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin" />
        Loading your plan…
      </div>
    )
  }

  const plan = result.value
  const items = plan?.content?.items ?? []
  if (!plan || items.length === 0) {
    return (
      <div className="max-w-2xl rounded-xl border bg-card p-4 text-sm text-muted-foreground">
        No plan to show yet.
      </div>
    )
  }

  const days = [...new Set(items.map((item) => item.day))].sort((a, b) => a - b)
  const total = items.reduce((sum, item) => sum + item.minutes, 0)

  return (
    <div className="w-full max-w-2xl space-y-3 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2">
        <CalendarDaysIcon className="size-5 text-primary" />
        <span className="font-semibold">Your study plan</span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <Badge variant="secondary">{days.length} days</Badge>
        <Badge variant="secondary">{items.length} steps</Badge>
        <Badge variant="secondary">{spellMinutes(total)} in total</Badge>
      </div>

      {plan.content.analysis && (
        <MathText className="text-sm leading-relaxed text-muted-foreground">
          {plan.content.analysis}
        </MathText>
      )}

      <StudyPlanSteps items={items} />

      {plan.content.encouragement && (
        <MathText className="text-sm leading-relaxed">
          {plan.content.encouragement}
        </MathText>
      )}
    </div>
  )
}
