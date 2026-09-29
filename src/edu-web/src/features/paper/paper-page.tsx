import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  ArrowLeft,
  CheckCircle2Icon,
  CircleDashedIcon,
  CircleDotIcon,
  ClockIcon,
  Loader2Icon,
  XCircleIcon,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import type {
  PaperDto,
  PaperItemDto,
  PaperItemResultDto,
} from '@/integrations/api/client'
import { useConfirmationDialog } from '@/components/confirmation-dialog'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Textarea } from '@/components/ui/textarea'
import {
  paperAtom,
  savePaperAnswersAtom,
  submitPaperAtom,
} from '@/data-acess/paper'
import { cn } from '@/lib/utils'

const OPTIONS = ['a', 'b', 'c', 'd'] as const

// When the student started, kept in the browser so a refresh does not reset the timer
const startKey = (paperId: string) => `paper-start-${paperId}`
const readStart = (paperId: string) => {
  try {
    const value = localStorage.getItem(startKey(paperId))
    return value ? Number(value) : null
  } catch {
    return null
  }
}
const writeStart = (paperId: string, at: number) => {
  try {
    localStorage.setItem(startKey(paperId), String(at))
  } catch {
    // Without storage the timer simply restarts after a refresh
  }
}

const formatTime = (ms: number) => {
  const total = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

const optionText = (item: PaperItemDto, option: string) =>
  String((item.options as Record<string, unknown> | null | undefined)?.[option] ?? '')

const countItems = (paper: PaperDto) =>
  paper.sections.reduce((n, s) => n + s.items.length, 0)

// --- Start screen ---

const StartScreen = ({ paper, onStart }: { paper: PaperDto; onStart: () => void }) => (
  <div className="mx-auto max-w-2xl space-y-4 p-4">
    <h1 className="text-2xl font-bold">{paper.title}</h1>
    <div className="flex flex-wrap gap-2 text-sm">
      <Badge variant="secondary">{paper.total_marks} marks</Badge>
      <Badge variant="secondary">{paper.time_limit_minutes} minutes</Badge>
      <Badge variant="secondary">{countItems(paper)} questions</Badge>
    </div>
    <ul className="space-y-1 text-sm">
      {paper.sections.map((section) => (
        <li key={section.id}>
          <span className="font-medium">{section.title}</span>
          <span className="text-muted-foreground">
            {' '}
            · {section.items.length} question{section.items.length === 1 ? '' : 's'},{' '}
            {section.items.reduce((n, i) => n + i.marks, 0)} marks
          </span>
        </li>
      ))}
    </ul>
    <div className="rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
      Answer as you would in the FBISE exam: for written questions give the
      formula, substitution and final answer with its unit. Your answers are
      saved as you type, and the paper is submitted automatically when time runs
      out. Written answers are marked by AI like an examiner (estimated marks).
    </div>
    <Button size="lg" onClick={onStart}>
      Start paper
    </Button>
  </div>
)

// --- Exam ---

const McqQuestion = ({
  item,
  number,
  value,
  onChange,
}: {
  item: PaperItemDto
  number: number
  value?: string
  onChange: (option: string) => void
}) => (
  <div id={`item-${item.id}`} className="space-y-2 rounded-xl border p-4">
    <div className="flex gap-2">
      <span className="font-semibold">{number}.</span>
      <MathText className="flex-1 font-medium">{item.question}</MathText>
    </div>
    <div className="grid gap-2 sm:grid-cols-2">
      {OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={cn(
            'flex gap-2 rounded-lg border p-2 text-left text-sm transition-colors hover:bg-accent/50',
            value === option && 'border-primary bg-primary/10 ring-1 ring-primary',
          )}
        >
          <span className="font-semibold uppercase">{option}.</span>
          <MathText className="flex-1">{optionText(item, option)}</MathText>
        </button>
      ))}
    </div>
  </div>
)

const WrittenQuestion = ({
  item,
  number,
  value,
  onChange,
}: {
  item: PaperItemDto
  number: number
  value?: string
  onChange: (text: string) => void
}) => (
  <div id={`item-${item.id}`} className="space-y-2 rounded-xl border p-4">
    <div className="flex gap-2">
      <span className="font-semibold">{number}.</span>
      <MathText className="flex-1 font-medium">{item.question}</MathText>
      <Badge variant="outline" className="h-fit shrink-0">
        {item.marks} marks
      </Badge>
    </div>
    <Textarea
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Write your answer: formula, substitution, answer with unit…"
      className={item.type === 'erq' ? 'min-h-56' : 'min-h-32'}
    />
  </div>
)

const ExamView = ({
  paper,
  startedAt,
  projectId,
}: {
  paper: PaperDto
  startedAt: number
  projectId: string
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(paper.answers ?? {}).map(([k, v]) => [k, String(v)])),
  )
  const [now, setNow] = useState(() => Date.now())
  const [submitting, setSubmitting] = useState(false)
  const save = useAtomSet(savePaperAnswersAtom, { mode: 'promise' })
  const submit = useAtomSet(submitPaperAtom, { mode: 'promise' })
  const confirmation = useConfirmationDialog()
  const submittedRef = useRef(false)
  const endsAt = startedAt + paper.time_limit_minutes * 60_000
  const remaining = endsAt - now
  const items = paper.sections.flatMap((s) => s.items)
  const answered = items.filter((i) => (answers[i.id] ?? '').trim()).length

  const doSubmit = useCallback(
    async (final: Record<string, string>) => {
      if (submittedRef.current) return
      submittedRef.current = true
      setSubmitting(true)
      try {
        await submit({ projectId, paperId: paper.id, answers: final })
      } catch {
        submittedRef.current = false
        toast.error('Could not submit, please try again')
      } finally {
        setSubmitting(false)
      }
    },
    [submit, projectId, paper.id],
  )

  // Clock, and automatic submission when time is up
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  useEffect(() => {
    if (remaining <= 0) void doSubmit(answers)
  }, [remaining, answers, doSubmit])

  // Save answers a moment after the student stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      void save({ projectId, paperId: paper.id, answers }).catch(() => undefined)
    }, 2000)
    return () => clearTimeout(timer)
  }, [answers, save, projectId, paper.id])

  const handleSubmit = async () => {
    const unanswered = items.length - answered
    const ok = await confirmation.open({
      title: 'Submit your paper?',
      description:
        unanswered > 0
          ? `${unanswered} question${unanswered === 1 ? ' is' : 's are'} not answered yet. You cannot change your answers after submitting.`
          : 'You cannot change your answers after submitting.',
      confirmLabel: 'Submit',
    })
    if (ok) await doSubmit(answers)
  }

  let number = 0
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4">
      <div className="sticky top-0 z-10 flex items-center gap-3 rounded-xl border bg-background/95 p-3 backdrop-blur">
        <ClockIcon className="size-4" />
        <span
          className={cn(
            'font-mono text-lg font-semibold',
            remaining < 60_000 ? 'text-red-600' : remaining < 300_000 && 'text-amber-600',
          )}
        >
          {formatTime(remaining)}
        </span>
        <span className="text-sm text-muted-foreground">
          {answered}/{items.length} answered
        </span>
        <Button className="ml-auto" onClick={handleSubmit} disabled={submitting}>
          {submitting && <Loader2Icon className="size-4 animate-spin" />}
          Submit paper
        </Button>
      </div>

      {submitting && (
        <div className="flex items-center gap-2 rounded-lg bg-muted p-3 text-sm">
          <Loader2Icon className="size-4 animate-spin" />
          Marking your paper like an FBISE examiner…
        </div>
      )}

      {paper.sections.map((section) => (
        <section key={section.id} className="space-y-3">
          <h2 className="text-lg font-semibold">{section.title}</h2>
          {section.items.map((item) => {
            number += 1
            const setValue = (value: string) =>
              setAnswers((prev) => ({ ...prev, [item.id]: value }))
            return item.type === 'mcq' ? (
              <McqQuestion
                key={item.id}
                item={item}
                number={number}
                value={answers[item.id]}
                onChange={setValue}
              />
            ) : (
              <WrittenQuestion
                key={item.id}
                item={item}
                number={number}
                value={answers[item.id]}
                onChange={setValue}
              />
            )
          })}
        </section>
      ))}

      <Button className="w-full" size="lg" onClick={handleSubmit} disabled={submitting}>
        Submit paper
      </Button>
    </div>
  )
}

// --- Results ---

const PointIcon = ({ awarded, marks }: { awarded: number; marks: number }) =>
  awarded >= marks ? (
    <CheckCircle2Icon className="size-4 shrink-0 text-emerald-600" />
  ) : awarded > 0 ? (
    <CircleDotIcon className="size-4 shrink-0 text-amber-500" />
  ) : (
    <CircleDashedIcon className="size-4 shrink-0 text-red-500" />
  )

const ItemResult = ({
  item,
  result,
  number,
}: {
  item: PaperItemDto
  result?: PaperItemResultDto
  number: number
}) => {
  if (!result) return null
  const full = result.awarded >= result.marks
  return (
    <div className="space-y-2 rounded-xl border p-4 text-sm">
      <div className="flex gap-2">
        <span className="font-semibold">{number}.</span>
        <MathText className="flex-1 font-medium">{item.question}</MathText>
        <span
          className={cn(
            'shrink-0 font-mono font-semibold',
            full ? 'text-emerald-600' : result.awarded > 0 ? 'text-amber-600' : 'text-red-600',
          )}
        >
          {result.awarded}/{result.marks}
        </span>
      </div>

      {item.type === 'mcq' ? (
        <div className="space-y-1 pl-5">
          {!full && (
            <div className="flex items-center gap-1 text-red-600">
              <XCircleIcon className="size-4" />
              Your answer:{' '}
              {result.chosen ? (
                <MathText>{`${result.chosen.toUpperCase()}. ${optionText(item, result.chosen)}`}</MathText>
              ) : (
                'not answered'
              )}
            </div>
          )}
          {result.correct_option && (
            <div className="flex items-center gap-1 text-emerald-700">
              <CheckCircle2Icon className="size-4" />
              <MathText>{`${result.correct_option.toUpperCase()}. ${optionText(item, result.correct_option)}`}</MathText>
            </div>
          )}
          {result.explanation && (
            <MathText className="text-muted-foreground">{result.explanation}</MathText>
          )}
        </div>
      ) : (
        <div className="space-y-2 pl-5">
          <div className="rounded-lg border bg-muted/40 p-2 whitespace-pre-wrap">
            {result.answer || <span className="text-muted-foreground">Not answered</span>}
          </div>
          {result.marking && (
            <>
              <ul className="space-y-1">
                {result.marking.points.map((point, index) => (
                  <li key={index} className="flex gap-2">
                    <PointIcon awarded={point.awarded} marks={point.marks} />
                    <div className="flex-1">
                      <MathText className="font-medium">{`${point.point} (${point.awarded}/${point.marks})`}</MathText>
                      {point.comment && (
                        <MathText className="text-muted-foreground">{point.comment}</MathText>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              {result.marking.feedback && (
                <div className="rounded-lg bg-muted/60 p-2">
                  <div className="font-medium">How to get full marks</div>
                  <MathText>{result.marking.feedback}</MathText>
                </div>
              )}
            </>
          )}
          {result.model_answer && (
            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button size="sm" variant="outline">
                  Show model answer
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 rounded-lg border p-3">
                <MathText>{result.model_answer}</MathText>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      )}
    </div>
  )
}

const ResultView = ({ paper, projectId }: { paper: PaperDto; projectId: string }) => {
  const result = paper.result
  if (!result) return null
  const byId = new Map(result.items.map((item) => [item.id, item]))
  let number = 0
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4">
      <div className="space-y-3 rounded-xl border p-5">
        <div className="text-sm text-muted-foreground">{paper.title}</div>
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="text-4xl font-bold">
            {result.score}/{result.max_score}
          </span>
          <span className="text-xl text-muted-foreground">{result.percent}%</span>
          <Badge className="text-base">{result.grade}</Badge>
          <span className="text-muted-foreground">{result.descriptor}</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          {result.sections.map((section) => (
            <div key={section.id} className="rounded-lg bg-muted/60 p-2 text-sm">
              <div className="text-muted-foreground">{section.title}</div>
              <div className="font-semibold">
                {section.score}/{section.max_score}
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          IBCC grade band for this paper only. Written answers are AI-estimated
          marks; your teacher&apos;s marking may differ slightly.
        </p>
        <Button variant="outline" asChild>
          <Link to="/dashboard/p/$projectId" params={{ projectId }}>
            Back to syllabus map
          </Link>
        </Button>
      </div>
      {paper.sections.map((section) => (
        <section key={section.id} className="space-y-3">
          <h2 className="text-lg font-semibold">{section.title}</h2>
          {section.items.map((item) => {
            number += 1
            return (
              <ItemResult key={item.id} item={item} result={byId.get(item.id)} number={number} />
            )
          })}
        </section>
      ))}
    </div>
  )
}

// --- Page ---

export const PaperPage = ({ projectId, paperId }: { projectId: string; paperId: string }) => {
  const paperResult = useAtomValue(paperAtom(`${projectId}:${paperId}`))
  const [startedAt, setStartedAt] = useState<number | null>(() => readStart(paperId))

  const start = () => {
    const at = Date.now()
    writeStart(paperId, at)
    setStartedAt(at)
  }

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-2">
        <div className="flex flex-1 items-center gap-2 px-3">
          <SidebarTrigger />
          <Button variant="ghost" size="icon" className="size-7" asChild>
            <Link to="/dashboard/p/$projectId" params={{ projectId }}>
              <ArrowLeft className="size-4" />
              <span className="sr-only">Back to subject</span>
            </Link>
          </Button>
          <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
          <span className="font-medium">Practice paper</span>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {Result.builder(paperResult)
          .onInitial(() => (
            <div className="flex items-center justify-center gap-2 p-12 text-muted-foreground">
              <Loader2Icon className="size-4 animate-spin" />
              Loading paper…
            </div>
          ))
          .onFailure(() => (
            <p className="p-12 text-center text-destructive">Could not load the paper</p>
          ))
          .onSuccess((paper) =>
            paper.status === 'submitted' ? (
              <ResultView paper={paper} projectId={projectId} />
            ) : startedAt ? (
              <ExamView paper={paper} startedAt={startedAt} projectId={projectId} />
            ) : (
              <StartScreen paper={paper} onStart={start} />
            ),
          )
          .render()}
      </div>
    </div>
  )
}
