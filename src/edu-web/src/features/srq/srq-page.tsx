import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { useNavigate } from '@tanstack/react-router'
import {
  CheckCircle2Icon,
  CircleDashedIcon,
  CircleDotIcon,
  Loader2Icon,
  RefreshCwIcon,
  SparklesIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { SrqAttemptDto, SrqQuestionDto } from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Textarea } from '@/components/ui/textarea'
import { createSrqAtom, markSrqAtom, srqDetailAtom } from '@/data-acess/srq'
import { cn } from '@/lib/utils'

const PointIcon = ({ awarded, marks }: { awarded: number; marks: number }) => {
  if (awarded >= marks)
    return <CheckCircle2Icon className="size-4 shrink-0 text-emerald-600" />
  if (awarded > 0)
    return <CircleDotIcon className="size-4 shrink-0 text-amber-500" />
  return <CircleDashedIcon className="size-4 shrink-0 text-red-500" />
}

const AttemptResult = ({ attempt }: { attempt: SrqAttemptDto }) => {
  const ratio = attempt.max_marks ? attempt.awarded_marks / attempt.max_marks : 0
  return (
    <div className="space-y-4 rounded-xl border p-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            AI-estimated marks
          </div>
          <div
            className={cn(
              'text-3xl font-bold',
              ratio >= 0.8
                ? 'text-emerald-600'
                : ratio >= 0.5
                  ? 'text-amber-600'
                  : 'text-red-600',
            )}
          >
            {attempt.awarded_marks} / {attempt.max_marks}
          </div>
        </div>
        <p className="max-w-xs text-right text-xs text-muted-foreground">
          Marked point by point like an FBISE examiner. Your teacher's marking
          may differ slightly.
        </p>
      </div>

      <ul className="space-y-2">
        {attempt.points.map((point, index) => (
          <li key={index} className="flex gap-2 text-sm">
            <PointIcon awarded={point.awarded} marks={point.marks} />
            <div className="min-w-0 flex-1">
              <div className="flex justify-between gap-2">
                <MathText className="font-medium">{point.point}</MathText>
                <span className="shrink-0 font-mono text-xs text-muted-foreground">
                  {point.awarded}/{point.marks}
                </span>
              </div>
              {point.comment && (
                <MathText className="text-muted-foreground">
                  {point.comment}
                </MathText>
              )}
            </div>
          </li>
        ))}
      </ul>

      {attempt.feedback && (
        <div className="rounded-lg bg-muted/60 p-3 text-sm">
          <div className="mb-1 font-medium">How to get full marks</div>
          <MathText>{attempt.feedback}</MathText>
        </div>
      )}

      <Collapsible>
        <CollapsibleTrigger asChild>
          <Button variant="outline" size="sm">
            Show model answer
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-3 rounded-lg border p-4 text-sm">
          <MathText>{attempt.model_answer}</MathText>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

const QuestionView = ({
  projectId,
  question,
  attempts,
}: {
  projectId: string
  question: SrqQuestionDto
  attempts: ReadonlyArray<SrqAttemptDto>
}) => {
  const navigate = useNavigate()
  const markSrq = useAtomSet(markSrqAtom, { mode: 'promise' })
  const createSrq = useAtomSet(createSrqAtom, { mode: 'promise' })
  const [answer, setAnswer] = useState('')
  const [marking, setMarking] = useState(false)
  const [creating, setCreating] = useState(false)
  const [retrying, setRetrying] = useState(false)
  // Shown straight away, before the refreshed question details arrive
  const [justMarked, setJustMarked] = useState<SrqAttemptDto | null>(null)

  const latest = justMarked ?? attempts.at(0)
  const showForm = !latest || retrying

  const handleSubmit = async () => {
    if (!answer.trim()) return
    setMarking(true)
    try {
      setJustMarked(await markSrq({ projectId, questionId: question.id, answer }))
      setRetrying(false)
      setAnswer('')
    } catch {
      toast.error('Could not mark your answer, please try again')
    } finally {
      setMarking(false)
    }
  }

  const handleNewQuestion = async () => {
    if (!question.slo_code) return
    setCreating(true)
    try {
      const next = await createSrq({ projectId, sloCode: question.slo_code })
      navigate({
        to: '/dashboard/p/$projectId/srq/$questionId',
        params: { projectId, questionId: next.id },
      })
    } catch {
      toast.error('Could not create a new question, please try again')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4">
      <div className="space-y-3 rounded-xl border bg-card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{question.marks} marks</Badge>
          {question.slo_code && (
            <Badge variant="outline" className="font-mono">
              SLO {question.slo_code}
            </Badge>
          )}
          <Badge variant="secondary">Short question (SRQ)</Badge>
        </div>
        <MathText className="text-base leading-relaxed">
          {question.question}
        </MathText>
      </div>

      {showForm ? (
        <div className="space-y-3">
          <Textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Write your answer as you would in the exam: formula, substitution, answer with unit..."
            className="min-h-40"
            disabled={marking}
          />
          <div className="flex items-center gap-3">
            <Button onClick={handleSubmit} disabled={marking || !answer.trim()}>
              {marking ? (
                <Loader2Icon className="size-4 animate-spin" />
              ) : (
                <SparklesIcon className="size-4" />
              )}
              {marking ? 'Marking like an examiner…' : 'Submit for marking'}
            </Button>
            {retrying && (
              <Button variant="ghost" onClick={() => setRetrying(false)}>
                Cancel
              </Button>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="space-y-1">
            <div className="text-sm font-medium">Your answer</div>
            <p className="whitespace-pre-wrap rounded-lg border p-3 text-sm">
              {latest.answer}
            </p>
          </div>
          <AttemptResult attempt={latest} />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setRetrying(true)}>
              <RefreshCwIcon className="size-4" />
              Try this question again
            </Button>
            {question.slo_code && (
              <Button onClick={handleNewQuestion} disabled={creating}>
                {creating && <Loader2Icon className="size-4 animate-spin" />}
                New question for this SLO
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export const SrqPage = ({
  projectId,
  questionId,
}: {
  projectId: string
  questionId: string
}) => {
  const detailResult = useAtomValue(srqDetailAtom(`${projectId}:${questionId}`))

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-2">
        <div className="flex flex-1 items-center gap-2 px-3">
          <SidebarTrigger />
          <Separator
            orientation="vertical"
            className="mr-2 data-[orientation=vertical]:h-4"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage className="font-medium">
                  Written answer practice
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {Result.builder(detailResult)
          .onInitial(() => (
            <div className="flex items-center justify-center gap-2 p-12 text-muted-foreground">
              <Loader2Icon className="size-4 animate-spin" />
              <span>Loading question…</span>
            </div>
          ))
          .onFailure(() => (
            <div className="p-12 text-center text-destructive">
              Failed to load the question
            </div>
          ))
          .onSuccess((detail) => (
            <QuestionView
              key={detail.question.id}
              projectId={projectId}
              question={detail.question}
              attempts={detail.attempts}
            />
          ))
          .render()}
      </div>
    </div>
  )
}
