import { Result, useAtomValue } from '@effect-atom/atom-react'
import { BadgeCheckIcon, ChevronRightIcon } from 'lucide-react'
import { MathText } from '@/components/math-text'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { sloExplainerAtom } from '@/data-acess/curriculum'

/** The prepared explainer for an SLO, when one has been written. */
export const SloExplainer = ({
  gradeSubjectId,
  sloCode,
}: {
  gradeSubjectId: string
  sloCode: string
}) => {
  const result = useAtomValue(sloExplainerAtom(`${gradeSubjectId}:${sloCode}`))
  if (!Result.isSuccess(result) || !result.value) return null
  const explainer = result.value

  return (
    <Collapsible defaultOpen className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center gap-2 p-3 text-left font-medium">
        <ChevronRightIcon className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        <span className="flex-1">Explainer</span>
        {explainer.reviewed && (
          <span className="flex items-center gap-1 text-xs font-normal text-emerald-600">
            <BadgeCheckIcon className="size-3.5" />
            Teacher-reviewed
          </span>
        )}
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t px-3 pb-3">
        <MathText className="prose prose-sm dark:prose-invert max-w-none [&_h3]:mt-3 [&_h3]:text-sm">
          {explainer.content}
        </MathText>
      </CollapsibleContent>
    </Collapsible>
  )
}
