import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  BadgeCheckIcon,
  CheckCircle2Icon,
  ChevronRightIcon,
  Loader2Icon,
  MessageCircleQuestionIcon,
  RotateCcwIcon,
  XCircleIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type {
  AttemptSummaryDto,
  QuizAttemptDto,
  QuizQuestionDto,
} from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { quizAtom, quizQuestionsAtom } from '@/data-acess/quiz'
import {
  latestQuizAttemptAtom,
  submitQuizAttemptAtom,
} from '@/data-acess/quiz-attempt'
import { cn } from '@/lib/utils'
import { QuizDownload } from '@/components/downloads'

const OPTIONS = ['a', 'b', 'c', 'd'] as const
type Option = (typeof OPTIONS)[number]

const optionText = (question: QuizQuestionDto, option: string) =>
  question[`option_${option as Option}`]

const normalized = (option: string) => option.trim().toLowerCase().slice(0, 1)

// A short message the student can send so the tutor explains what they got wrong
const mistakesMessage = (
  questions: ReadonlyArray<QuizQuestionDto>,
  attempt: QuizAttemptDto,
) => {
  const wrong = attempt.answers
    .map((answer) => ({
      answer,
      question: questions.find((q) => q.id === answer.question_id),
    }))
    .filter(({ answer, question }) => question && !answer.is_correct)
  const lines = wrong.map(({ answer, question }, index) => {
    const q = question as QuizQuestionDto
    const chosen = answer.chosen
      ? `${answer.chosen.toUpperCase()} (${optionText(q, answer.chosen)})`
      : 'nothing'
    return `${index + 1}. ${q.question_text.slice(0, 200)}\n   I chose ${chosen}; the correct answer is ${answer.correct_option.toUpperCase()} (${optionText(q, answer.correct_option)}).`
  })
  return `I scored ${attempt.score}/${attempt.max_score} on the quiz. I got these wrong:\n${lines.join('\n')}\nPlease explain my mistakes.`
}

// Every try is kept: "Attempt 1 3/5 · Attempt 2 5/5"
const AttemptHistory = ({
  history,
  current,
}: {
  history: ReadonlyArray<AttemptSummaryDto>
  current: number
}) =>
  history.length > 1 ? (
    <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
      <span>Your attempts:</span>
      {history.map((item) => (
        <span
          key={item.id}
          className={cn(
            'rounded-full border px-2 py-0.5',
            item.number === current && 'border-primary text-foreground',
          )}
        >
          #{item.number} · {item.score}/{item.max_score}
        </span>
      ))}
    </div>
  ) : null

const ResultView = ({
  questions,
  attempt,
  history,
  onRetry,
  onAsk,
  openLink,
}: {
  questions: ReadonlyArray<QuizQuestionDto>
  attempt: QuizAttemptDto
  history: ReadonlyArray<AttemptSummaryDto>
  onRetry: () => void
  onAsk?: (text: string) => void
  openLink: React.ReactNode
}) => {
  const [open, setOpen] = useState<string | null>(null)
  const ratio = attempt.max_score ? attempt.score / attempt.max_score : 0
  const wrongCount = attempt.answers.filter((a) => !a.is_correct).length

  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span
          className={cn(
            'text-3xl font-bold',
            ratio >= 0.8
              ? 'text-emerald-600'
              : ratio >= 0.5
                ? 'text-amber-600'
                : 'text-red-600',
          )}
        >
          {attempt.score}/{attempt.max_score}
        </span>
        <span className="text-sm text-muted-foreground">
          {ratio >= 0.8
            ? 'Excellent!'
            : ratio >= 0.5
              ? 'Good try!'
              : 'Keep practising!'}
        </span>
        <Badge variant="secondary" className="ml-auto">
          Attempt {attempt.number}
        </Badge>
      </div>
      <AttemptHistory history={history} current={attempt.number} />

      <ul className="space-y-1">
        {attempt.answers.map((answer, index) => {
          const question = questions.find((q) => q.id === answer.question_id)
          if (!question) return null
          const expanded = open === answer.question_id
          return (
            <li key={answer.question_id} className="rounded-lg border">
              <button
                type="button"
                onClick={() => setOpen(expanded ? null : answer.question_id)}
                className="flex w-full items-start gap-2 p-2 text-left text-sm"
              >
                {answer.is_correct ? (
                  <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                ) : (
                  <XCircleIcon className="mt-0.5 size-4 shrink-0 text-red-500" />
                )}
                <span className="shrink-0 font-medium">Q{index + 1}.</span>
                <MathText className="line-clamp-2 flex-1">
                  {question.question_text}
                </MathText>
              </button>
              {expanded && (
                <div className="space-y-1 border-t px-3 py-2 text-sm">
                  {!answer.is_correct && (
                    <div className="text-red-600">
                      Your answer:{' '}
                      {answer.chosen
                        ? `${answer.chosen.toUpperCase()}. ${optionText(question, answer.chosen)}`
                        : 'skipped'}
                    </div>
                  )}
                  <div className="flex gap-1 text-emerald-700">
                    <span>Correct: {answer.correct_option.toUpperCase()}.</span>
                    <MathText>
                      {optionText(question, answer.correct_option)}
                    </MathText>
                  </div>
                  {question.explanation && (
                    <MathText className="text-muted-foreground">
                      {question.explanation}
                    </MathText>
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ul>

      <div className="flex flex-wrap gap-2">
        {wrongCount > 0 && onAsk && (
          <Button
            size="sm"
            onClick={() => onAsk(mistakesMessage(questions, attempt))}
          >
            <MessageCircleQuestionIcon className="size-4" />
            Ask tutor about my mistakes
          </Button>
        )}
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RotateCcwIcon className="size-4" />
          Try again
        </Button>
        {openLink}
      </div>
    </div>
  )
}

const Player = ({
  questions,
  attemptNumber,
  onFinish,
  submitting,
}: {
  questions: ReadonlyArray<QuizQuestionDto>
  attemptNumber: number
  onFinish: (answers: Record<string, string | null>) => void
  submitting: boolean
}) => {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const question = questions[index]
  const chosen = answers[question.id] as string | undefined
  const correct = normalized(question.correct_option)
  const last = index === questions.length - 1

  const choose = (option: Option) => {
    if (chosen) return
    setAnswers((prev) => ({ ...prev, [question.id]: option }))
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-1">
        {questions.map((q, i) => (
          <span
            key={q.id}
            className={cn(
              'h-1.5 flex-1 rounded-full bg-muted',
              answers[q.id] &&
                (normalized(answers[q.id]) === normalized(q.correct_option)
                  ? 'bg-emerald-500'
                  : 'bg-red-500'),
              i === index && !answers[q.id] && 'bg-primary/60',
            )}
          />
        ))}
      </div>

      <div className="text-xs text-muted-foreground">
        Question {index + 1} of {questions.length}
        {attemptNumber > 1 && ` · Attempt ${attemptNumber}`}
      </div>
      <MathText className="font-medium leading-relaxed">
        {question.question_text}
      </MathText>

      <div className="grid gap-2">
        {OPTIONS.map((option) => {
          const isCorrect = option === correct
          const isChosen = chosen === option
          return (
            <button
              key={option}
              type="button"
              disabled={!!chosen}
              onClick={() => choose(option)}
              className={cn(
                'flex gap-2 rounded-lg border p-3 text-left text-sm transition-colors',
                !chosen && 'hover:border-primary/60 hover:bg-accent/50',
                chosen && isCorrect && 'border-emerald-500 bg-emerald-500/10',
                chosen &&
                  isChosen &&
                  !isCorrect &&
                  'border-red-500 bg-red-500/10',
              )}
            >
              <span className="font-semibold uppercase">{option}.</span>
              <MathText className="flex-1">
                {optionText(question, option)}
              </MathText>
              {chosen && isCorrect && (
                <CheckCircle2Icon className="size-4 shrink-0 text-emerald-600" />
              )}
              {chosen && isChosen && !isCorrect && (
                <XCircleIcon className="size-4 shrink-0 text-red-500" />
              )}
            </button>
          )
        })}
      </div>

      {chosen && (
        <div className="space-y-2">
          <div
            className={cn(
              'text-sm font-medium',
              chosen === correct ? 'text-emerald-600' : 'text-red-600',
            )}
          >
            {chosen === correct
              ? 'Correct!'
              : `Not quite. The answer is ${correct.toUpperCase()}.`}
          </div>
          {question.explanation && (
            <MathText className="rounded-lg bg-muted/60 p-3 text-sm">
              {question.explanation}
            </MathText>
          )}
          <Button
            size="sm"
            disabled={submitting}
            onClick={() => (last ? onFinish(answers) : setIndex(index + 1))}
          >
            {submitting && <Loader2Icon className="size-4 animate-spin" />}
            {last ? 'See my score' : 'Next question'}
          </Button>
        </div>
      )}
    </div>
  )
}

/** An MCQ quiz the student answers inside the chat; the result is kept and counts for mastery. */
export const ChatQuizCard = ({
  projectId,
  quizId,
  onAsk,
}: {
  projectId: string
  quizId: string
  onAsk?: (text: string) => void
}) => {
  const key = `${projectId}:${quizId}`
  const quizResult = useAtomValue(quizAtom(key))
  const questionsResult = useAtomValue(quizQuestionsAtom(key))
  const attemptResult = useAtomValue(latestQuizAttemptAtom(key))
  const submit = useAtomSet(submitQuizAttemptAtom, { mode: 'promise' })
  const [retrying, setRetrying] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [fresh, setFresh] = useState<QuizAttemptDto | null>(null)

  const quiz = Result.isSuccess(quizResult) ? quizResult.value : null
  const questions = Result.isSuccess(questionsResult)
    ? questionsResult.value
    : null
  const state = Result.isSuccess(attemptResult) ? attemptResult.value : null
  const saved = state?.attempt ?? null
  const history = state?.history ?? []
  const attempt = retrying ? null : (fresh ?? saved)

  const handleFinish = async (answers: Record<string, string | null>) => {
    setSubmitting(true)
    try {
      setFresh(await submit({ projectId, quizId, answers }))
      setRetrying(false)
    } catch {
      toast.error('Could not save your answers, please try again')
    } finally {
      setSubmitting(false)
    }
  }

  const openLink = (
    <Button size="sm" variant="ghost" asChild>
      <Link
        to="/dashboard/p/$projectId/q/$quizId"
        params={{ projectId, quizId }}
      >
        Open full quiz
        <ChevronRightIcon className="size-4" />
      </Link>
    </Button>
  )

  return (
    <div className="w-full max-w-2xl space-y-3 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{quiz?.name ?? 'Quiz'}</span>
        {quiz?.slo_code && (
          <Badge variant="outline" className="font-mono">
            {quiz.slo_code}
          </Badge>
        )}
        {quiz?.description?.includes('checked by a subject teacher') && (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <BadgeCheckIcon className="size-3.5" />
            Teacher-checked
          </span>
        )}
        <div className="ml-auto">
          <QuizDownload projectId={projectId} quizId={quizId} />
        </div>
      </div>

      {!questions || !Result.isSuccess(attemptResult) ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" />
          Loading quiz…
        </div>
      ) : questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          This quiz has no questions.
        </p>
      ) : attempt ? (
        <ResultView
          questions={questions}
          attempt={attempt}
          history={history}
          onRetry={() => {
            setFresh(null)
            setRetrying(true)
          }}
          onAsk={onAsk}
          openLink={openLink}
        />
      ) : (
        <Player
          // Re-mount so a retry starts from the first question
          key={`${retrying}-${saved?.id ?? 'new'}`}
          questions={questions}
          attemptNumber={history.length + 1}
          onFinish={handleFinish}
          submitting={submitting}
        />
      )}
    </div>
  )
}
