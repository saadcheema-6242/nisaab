import { CheckCircle2Icon, PencilLineIcon, SparklesIcon } from 'lucide-react'
import { useState } from 'react'
import { parseOutput } from './tool-status'
import type { ToolCallPartDto } from '@/integrations/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

type SetupQuestion = {
  id: string
  question: string
  options: Array<string>
  multiple: boolean
  recommended: Array<string>
}

type Kind = 'quiz' | 'flashcards' | 'mind_map' | 'paper'

export type PracticeSetup = {
  kind: Kind
  topic: string
  questions: Array<SetupQuestion>
}

const LABELS: Record<Kind, { title: string; button: string; name: string }> = {
  quiz: {
    title: 'Before I make your quiz',
    button: 'Make my quiz',
    name: 'Quiz',
  },
  flashcards: {
    title: 'Before I make your flashcards',
    button: 'Make my flashcards',
    name: 'Flashcards',
  },
  mind_map: {
    title: 'Before I draw your mind map',
    button: 'Draw my mind map',
    name: 'Mind map',
  },
  paper: {
    title: 'Before I set your paper',
    button: 'Make my paper',
    name: 'Paper',
  },
}

const isKind = (value: unknown): value is Kind =>
  value === 'quiz' ||
  value === 'flashcards' ||
  value === 'mind_map' ||
  value === 'paper'

/** The questions the tutor asked before making practice, from its finished tool call. */
export const parseSetup = (toolCall: ToolCallPartDto): PracticeSetup | null => {
  if (toolCall.tool_state !== 'output-available') return null
  const output = parseOutput(toolCall.tool_output)
  if (!output || typeof output !== 'object') return null
  const { kind, topic, questions } = output as Record<string, unknown>
  if (!Array.isArray(questions) || questions.length === 0) return null
  return {
    kind: isKind(kind) ? kind : 'quiz',
    topic: typeof topic === 'string' ? topic : '',
    questions: questions as Array<SetupQuestion>,
  }
}

/**
 * A few tappable questions the tutor asks before making a quiz, flashcards, a mind
 * map or a paper. The answers go back to the tutor as the student's next message.
 */
export const ChatAskCard = ({
  setup,
  answered,
  onAsk,
}: {
  setup: PracticeSetup
  // A later message exists, so these questions were already answered
  answered: boolean
  onAsk?: (text: string) => void
}) => {
  const labels = LABELS[setup.kind]
  const [picked, setPicked] = useState<Record<string, Array<string>>>(() =>
    Object.fromEntries(setup.questions.map((q) => [q.id, q.recommended])),
  )
  const [other, setOther] = useState<Record<string, string>>({})
  const [typing, setTyping] = useState<Record<string, boolean>>({})
  const [sent, setSent] = useState(false)
  const locked = answered || sent

  const toggle = (question: SetupQuestion, option: string) => {
    if (locked) return
    setPicked((prev) => {
      const current = prev[question.id] ?? []
      if (question.multiple) {
        return {
          ...prev,
          [question.id]: current.includes(option)
            ? current.filter((o) => o !== option)
            : [...current, option],
        }
      }
      return { ...prev, [question.id]: current[0] === option ? [] : [option] }
    })
  }

  const answersFor = (question: SetupQuestion) => {
    const typed = (question.id in other ? other[question.id] : '').trim()
    return [...(picked[question.id] ?? []), ...(typed ? [typed] : [])]
  }

  const send = (youDecide: boolean) => {
    const lines = setup.questions.map((question) => {
      const answers = youDecide ? question.recommended : answersFor(question)
      return `- ${question.question} ${answers.length ? answers.join(', ') : 'you decide'}`
    })
    const topic = setup.topic ? ` (${setup.topic})` : ''
    const text = `${labels.name} setup${topic}:\n${lines.join('\n')}\n${
      youDecide ? 'You decide the rest. ' : ''
    }Please make it now.`
    setSent(true)
    onAsk?.(text)
  }

  if (answered && !sent) {
    return (
      <div className="flex w-full max-w-2xl items-center gap-2 rounded-xl border bg-card px-4 py-3 text-sm text-muted-foreground">
        <CheckCircle2Icon className="size-4 shrink-0 text-emerald-600" />
        You answered {setup.questions.length} quick questions about this{' '}
        {labels.name.toLowerCase()}.
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl space-y-4 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2 font-semibold">
        <SparklesIcon className="size-4 text-primary" />
        {labels.title}
      </div>

      {setup.questions.map((question, index) => (
        <div key={question.id} className="space-y-2">
          <div className="text-sm font-medium">
            {index + 1}. {question.question}
            {question.multiple && (
              <span className="font-normal text-muted-foreground">
                {' '}
                (pick any)
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {question.options.map((option) => {
              const selected = (picked[question.id] ?? []).includes(option)
              return (
                <button
                  key={option}
                  type="button"
                  disabled={locked}
                  onClick={() => toggle(question, option)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-left text-sm transition-colors',
                    selected
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'hover:border-primary/60 hover:bg-accent/50',
                    locked && !selected && 'opacity-50',
                  )}
                >
                  {option}
                </button>
              )
            })}
            {!locked && !typing[question.id] && (
              <button
                type="button"
                onClick={() =>
                  setTyping((prev) => ({ ...prev, [question.id]: true }))
                }
                className="flex items-center gap-1 rounded-full border border-dashed px-3 py-1 text-sm text-muted-foreground hover:bg-accent/50"
              >
                <PencilLineIcon className="size-3.5" />
                Other…
              </button>
            )}
          </div>
          {typing[question.id] && (
            <Input
              autoFocus
              disabled={locked}
              value={other[question.id] ?? ''}
              onChange={(e) =>
                setOther((prev) => ({ ...prev, [question.id]: e.target.value }))
              }
              placeholder="Type your answer"
              className="h-9 max-w-sm"
            />
          )}
        </div>
      ))}

      {sent ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2Icon className="size-4" />
          Got it, making it now…
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => send(false)}>
            {labels.button}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => send(true)}>
            You decide
          </Button>
        </div>
      )}
    </div>
  )
}
