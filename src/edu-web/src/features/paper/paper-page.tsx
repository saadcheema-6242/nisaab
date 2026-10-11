import {
  Result,
  useAtomRefresh,
  useAtomSet,
  useAtomValue,
} from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  AlertCircleIcon,
  ArrowLeft,
  CheckCircle2Icon,
  CircleDashedIcon,
  CircleDotIcon,
  ClockIcon,
  Loader2Icon,
  XCircleIcon,
} from 'lucide-react'
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  countQuestions,
  formatMarks,
  hasChoices,
  sectionBlocks,
  sectionMarks,
  sectionQuestions,
} from './paper-utils'
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
import { ThinkingDots } from '@/components/ui/thinking-dots'
import { usePollWhile } from '@/hooks/use-poll-while'
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
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = String(total % 60).padStart(2, '0')
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${seconds}`
    : `${minutes}:${seconds}`
}

const optionText = (item: PaperItemDto, option: string) =>
  String((item.options as Record<string, unknown> | null | undefined)?.[option] ?? '')

const filled = (value?: string) => Boolean((value ?? '').trim())

// The question of a choice pair the student is answering: the one they picked, else
// the one they wrote in, else (a)
const initialChoices = (paper: PaperDto, answers: Record<string, string>) => {
  const choices: Record<string, string> = {}
  for (const section of paper.sections)
    for (const block of sectionBlocks(section))
      if (block.kind === 'choice') {
        const written = block.items.find((i) => filled(answers[i.id]))
        choices[block.group] = (written ?? block.items[0]).choice ?? 'a'
      }
  return choices
}

const PaperBadges = ({ paper }: { paper: PaperDto }) => (
  <div className="flex flex-wrap gap-2 text-sm">
    <Badge variant="secondary">{formatMarks(paper.total_marks)} marks</Badge>
    <Badge variant="secondary">{paper.time_limit_minutes} minutes</Badge>
    {paper.status !== 'preparing' && (
      <Badge variant="secondary">{countQuestions(paper)} questions</Badge>
    )}
  </div>
)

// --- Preparing / failed ---

const PreparingView = ({
  paper,
  timedOut,
  onCheck,
}: {
  paper: PaperDto
  timedOut: boolean
  onCheck: () => void
}) => (
  <div className="mx-auto max-w-2xl space-y-4 p-4">
    <h1 className="text-2xl font-bold">{paper.title}</h1>
    <PaperBadges paper={paper} />
    <div className="flex gap-3 rounded-lg bg-muted/60 p-4 text-sm">
      <ThinkingDots className="mt-1.5 shrink-0" label="Setting your paper" />
      <div className="space-y-1">
        <div className="thinking-text font-medium">Setting your paper…</div>
        <div className="text-muted-foreground">
          Choosing MCQs, writing stimulus sets and questions with an internal
          choice across the syllabus, like an FBISE paper setter. This usually
          takes one to three minutes. You can leave this page and come back.
        </div>
      </div>
    </div>
    {timedOut && (
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        This is taking longer than usual.
        <Button size="sm" variant="outline" onClick={onCheck}>
          Check again
        </Button>
      </div>
    )}
  </div>
)

const FailedView = ({ paper, projectId }: { paper: PaperDto; projectId: string }) => (
  <div className="mx-auto max-w-2xl space-y-4 p-4">
    <h1 className="text-2xl font-bold">{paper.title}</h1>
    <div className="flex gap-3 rounded-lg border border-destructive/40 p-4 text-sm">
      <AlertCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div>
        This paper could not be set. Please make a new one from the syllabus
        map, or ask the tutor for a paper.
      </div>
    </div>
    <Button variant="outline" asChild>
      <Link to="/dashboard/p/$projectId" params={{ projectId }}>
        Back to syllabus map
      </Link>
    </Button>
  </div>
)

// --- Start screen ---

const StartScreen = ({ paper, onStart }: { paper: PaperDto; onStart: () => void }) => (
  <div className="mx-auto max-w-2xl space-y-4 p-4">
    <h1 className="text-2xl font-bold">{paper.title}</h1>
    <PaperBadges paper={paper} />
    <ul className="space-y-1 text-sm">
      {paper.sections.map((section) => {
        const questions = sectionQuestions(section)
        return (
          <li key={section.id}>
            <span className="font-medium">{section.title}</span>
            <span className="text-muted-foreground">
              {' '}
              · {questions} question{questions === 1 ? '' : 's'},{' '}
              {formatMarks(sectionMarks(section))} marks
            </span>
          </li>
        )
      })}
    </ul>
    <div className="rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
      Answer as you would in the FBISE exam: for written questions give the
      formula, substitution and final answer with its unit.
      {hasChoices(paper) &&
        ' In Sections B and C, choose (a) or (b) of each question and answer only that one.'}{' '}
      Your answers are saved as you type, and the paper is submitted
      automatically when time runs out. Written answers are marked by AI like
      an examiner (estimated marks).
    </div>
    <Button size="lg" onClick={onStart}>
      Start paper
    </Button>
  </div>
)

// --- Exam ---

const StimulusBox = ({
  stimulus,
  from,
  to,
}: {
  stimulus: string
  from: number
  to: number
}) => (
  <div className="space-y-2 rounded-xl border-l-4 border-primary bg-primary/5 p-4">
    <div className="text-sm font-semibold">
      Read the following and answer questions {from} to {to}.
    </div>
    <MathText>{stimulus}</MathText>
  </div>
)

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
        {formatMarks(item.marks)} marks
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

// An internal choice: both questions are shown, the student answers one
const ChoiceQuestion = ({
  items,
  number,
  chosen,
  answers,
  onChoose,
  onChange,
}: {
  items: Array<PaperItemDto>
  number: number
  chosen: string
  answers: Record<string, string>
  onChoose: (choice: string) => void
  onChange: (itemId: string, text: string) => void
}) => {
  const current = items.find((i) => i.choice === chosen) ?? items[0]
  return (
    <div id={`item-${current.id}`} className="space-y-3 rounded-xl border p-4">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{number}.</span>
        <span className="text-sm text-muted-foreground">
          Answer either (a) or (b)
        </span>
        <Badge variant="outline" className="ml-auto h-fit shrink-0">
          {formatMarks(current.marks)} marks
        </Badge>
      </div>
      {items.map((item, index) => (
        <Fragment key={item.id}>
          {index > 0 && (
            <div className="text-center text-xs font-semibold tracking-widest text-muted-foreground">
              OR
            </div>
          )}
          <button
            type="button"
            onClick={() => onChoose(item.choice ?? 'a')}
            aria-pressed={item.id === current.id}
            className={cn(
              'flex w-full gap-2 rounded-lg border p-3 text-left transition-colors hover:bg-accent/50',
              item.id === current.id && 'border-primary bg-primary/5 ring-1 ring-primary',
            )}
          >
            <span className="font-semibold">({item.choice})</span>
            <MathText className="flex-1">{item.question}</MathText>
          </button>
        </Fragment>
      ))}
      <Textarea
        value={answers[current.id] ?? ''}
        onChange={(e) => onChange(current.id, e.target.value)}
        placeholder={`Write your answer to (${current.choice}): formula, substitution, answer with unit…`}
        className={current.type === 'erq' ? 'min-h-56' : 'min-h-32'}
      />
    </div>
  )
}

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
  const [choices, setChoices] = useState<Record<string, string>>(() =>
    initialChoices(paper, answers),
  )
  const [now, setNow] = useState(() => Date.now())
  const [submitting, setSubmitting] = useState(false)
  const save = useAtomSet(savePaperAnswersAtom, { mode: 'promise' })
  const submit = useAtomSet(submitPaperAtom, { mode: 'promise' })
  const confirmation = useConfirmationDialog()
  const submittedRef = useRef(false)
  const endsAt = startedAt + paper.time_limit_minutes * 60_000
  const remaining = endsAt - now
  const blocks = useMemo(() => paper.sections.flatMap(sectionBlocks), [paper])

  // Only the chosen question of each pair is handed in
  const handedIn = useCallback(
    (all: Record<string, string>) => {
      const skipped = new Set(
        blocks.flatMap((block) =>
          block.kind === 'choice'
            ? block.items.filter((i) => i.choice !== choices[block.group]).map((i) => i.id)
            : [],
        ),
      )
      return Object.fromEntries(Object.entries(all).filter(([id]) => !skipped.has(id)))
    },
    [blocks, choices],
  )

  const total = blocks.reduce((n, b) => n + (b.kind === 'stimulus' ? b.items.length : 1), 0)
  const answered = blocks.reduce((n, block) => {
    if (block.kind === 'single') return n + (filled(answers[block.item.id]) ? 1 : 0)
    if (block.kind === 'stimulus')
      return n + block.items.filter((i) => filled(answers[i.id])).length
    const current = block.items.find((i) => i.choice === choices[block.group])
    return n + (current && filled(answers[current.id]) ? 1 : 0)
  }, 0)

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
    if (remaining <= 0) void doSubmit(handedIn(answers))
  }, [remaining, answers, doSubmit, handedIn])

  // Save answers a moment after the student stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      void save({ projectId, paperId: paper.id, answers }).catch(() => undefined)
    }, 2000)
    return () => clearTimeout(timer)
  }, [answers, save, projectId, paper.id])

  const handleSubmit = async () => {
    const unanswered = total - answered
    const ok = await confirmation.open({
      title: 'Submit your paper?',
      description:
        unanswered > 0
          ? `${unanswered} question${unanswered === 1 ? ' is' : 's are'} not answered yet. You cannot change your answers after submitting.`
          : 'You cannot change your answers after submitting.',
      confirmLabel: 'Submit',
    })
    if (ok) await doSubmit(handedIn(answers))
  }

  const setAnswer = (itemId: string, value: string) =>
    setAnswers((prev) => ({ ...prev, [itemId]: value }))

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
          {answered}/{total} answered
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
          {sectionBlocks(section).map((block) => {
            if (block.kind === 'choice') {
              number += 1
              return (
                <ChoiceQuestion
                  key={block.group}
                  items={block.items}
                  number={number}
                  chosen={choices[block.group] ?? 'a'}
                  answers={answers}
                  onChoose={(choice) =>
                    setChoices((prev) => ({ ...prev, [block.group]: choice }))
                  }
                  onChange={setAnswer}
                />
              )
            }
            const items = block.kind === 'single' ? [block.item] : block.items
            const from = number + 1
            const questions = items.map((item) => {
              number += 1
              return item.type === 'mcq' ? (
                <McqQuestion
                  key={item.id}
                  item={item}
                  number={number}
                  value={answers[item.id]}
                  onChange={(value) => setAnswer(item.id, value)}
                />
              ) : (
                <WrittenQuestion
                  key={item.id}
                  item={item}
                  number={number}
                  value={answers[item.id]}
                  onChange={(value) => setAnswer(item.id, value)}
                />
              )
            })
            return block.kind === 'stimulus' ? (
              <div key={block.group} className="space-y-3">
                <StimulusBox stimulus={block.stimulus} from={from} to={number} />
                {questions}
              </div>
            ) : (
              questions
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

const ModelAnswer = ({ text, open }: { text: string; open?: boolean }) =>
  open ? (
    <div className="rounded-lg border p-3">
      <div className="mb-1 font-medium">Model answer</div>
      <MathText>{text}</MathText>
    </div>
  ) : (
    <Collapsible>
      <CollapsibleTrigger asChild>
        <Button size="sm" variant="outline">
          Show model answer
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 rounded-lg border p-3">
        <MathText>{text}</MathText>
      </CollapsibleContent>
    </Collapsible>
  )

const ItemResult = ({
  item,
  result,
  number,
  alternative,
}: {
  item: PaperItemDto
  result?: PaperItemResultDto
  number: number
  // The question of a choice pair the student did not answer: only its model answer
  alternative?: boolean
}) => {
  if (!result) return null
  const full = result.awarded >= result.marks
  const label = item.choice ? `${number} (${item.choice}).` : `${number}.`
  return (
    <div className="space-y-2 rounded-xl border p-4 text-sm">
      <div className="flex gap-2">
        <span className="shrink-0 font-semibold">{label}</span>
        <MathText className="flex-1 font-medium">{item.question}</MathText>
        {!alternative && (
          <span
            className={cn(
              'shrink-0 font-mono font-semibold',
              full ? 'text-emerald-600' : result.awarded > 0 ? 'text-amber-600' : 'text-red-600',
            )}
          >
            {formatMarks(result.awarded)}/{formatMarks(result.marks)}
          </span>
        )}
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
      ) : alternative ? (
        <div className="pl-5">
          {result.model_answer && <ModelAnswer text={result.model_answer} open />}
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
                      <MathText className="font-medium">{`${point.point} (${formatMarks(point.awarded)}/${formatMarks(point.marks)})`}</MathText>
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
          {result.model_answer && <ModelAnswer text={result.model_answer} />}
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
            {formatMarks(result.score)}/{formatMarks(result.max_score)}
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
                {formatMarks(section.score)}/{formatMarks(section.max_score)}
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
          {sectionBlocks(section).map((block) => {
            if (block.kind === 'choice') {
              number += 1
              // The question the student answered (the better one if both), else (a)
              const answered = block.items
                .filter((i) => byId.get(i.id)?.answer)
                .sort((x, y) => (byId.get(y.id)?.awarded ?? 0) - (byId.get(x.id)?.awarded ?? 0))
              const shown = answered.at(0) ?? block.items[0]
              const others = block.items.filter((i) => i.id !== shown.id)
              return (
                <div key={block.group} className="space-y-2">
                  <ItemResult item={shown} result={byId.get(shown.id)} number={number} />
                  {others.map((other) => (
                    <Collapsible key={other.id}>
                      <CollapsibleTrigger asChild>
                        <Button size="sm" variant="ghost" className="text-muted-foreground">
                          See the other choice ({other.choice}) and its model answer
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2">
                        <ItemResult
                          item={other}
                          result={byId.get(other.id)}
                          number={number}
                          alternative
                        />
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )
            }
            const items = block.kind === 'single' ? [block.item] : block.items
            const from = number + 1
            const results = items.map((item) => {
              number += 1
              return (
                <ItemResult key={item.id} item={item} result={byId.get(item.id)} number={number} />
              )
            })
            return block.kind === 'stimulus' ? (
              <div key={block.group} className="space-y-3">
                <StimulusBox stimulus={block.stimulus} from={from} to={number} />
                {results}
              </div>
            ) : (
              results
            )
          })}
        </section>
      ))}
    </div>
  )
}

// --- Page ---

export const PaperPage = ({ projectId, paperId }: { projectId: string; paperId: string }) => {
  const atom = paperAtom(`${projectId}:${paperId}`)
  const paperResult = useAtomValue(atom)
  const refresh = useAtomRefresh(atom)
  const [startedAt, setStartedAt] = useState<number | null>(() => readStart(paperId))

  // Board papers are set by the worker; keep checking until they are ready
  const preparing =
    Result.isSuccess(paperResult) && paperResult.value.status === 'preparing'
  const timedOut = usePollWhile(preparing, refresh, {
    intervalMs: 5000,
    maxMs: 6 * 60_000,
  })

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
            ) : paper.status === 'preparing' ? (
              <PreparingView paper={paper} timedOut={timedOut} onCheck={refresh} />
            ) : paper.status === 'failed' ? (
              <FailedView paper={paper} projectId={projectId} />
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
