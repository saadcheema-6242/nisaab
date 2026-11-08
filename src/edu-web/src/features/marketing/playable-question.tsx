import { AnimatePresence, motion } from 'motion/react'
import { CheckIcon, RotateCcwIcon, XIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Question = {
  subject: string
  domain: string
  colour: string
  question: string
  options: Array<string>
  answer: number
  why: string
}

// Written in the FBISE style: one clear outcome, four plausible options and a
// reason that explains the marking, not just the letter.
const questions: Array<Question> = [
  {
    subject: 'Physics',
    domain: 'Rotational and Circular Motion',
    colour: '#38BDF8',
    question:
      'A body moves in a circle of radius r at constant speed v. The magnitude of its acceleration is',
    options: ['zero', 'v / r', 'v² / r', 'v² r'],
    answer: 2,
    why: 'Speed is constant but direction is not, so the body is accelerating. That centripetal acceleration has magnitude v² / r and points toward the centre.',
  },
  {
    subject: 'Chemistry',
    domain: 'Periodicity',
    colour: '#34D399',
    question:
      'Which of these elements has the highest first ionisation energy?',
    options: ['Na', 'Mg', 'Al', 'Si'],
    answer: 3,
    why: 'Ionisation energy rises across a period as nuclear charge grows, so silicon is highest here. (Mg beats Al because Al loses a 3p electron, which is easier than breaking Mg’s filled 3s.)',
  },
  {
    subject: 'Biology',
    domain: 'Cell Cycle',
    colour: '#FB7185',
    question:
      'During which phase of mitosis do chromosomes line up along the cell’s equator?',
    options: ['Prophase', 'Metaphase', 'Anaphase', 'Telophase'],
    answer: 1,
    why: 'In metaphase the chromosomes settle on the metaphase plate, each held by spindle fibres from both poles before they are pulled apart.',
  },
]

const letters = ['A', 'B', 'C', 'D']

export const PlayableQuestion = ({ className }: { className?: string }) => {
  const [index, setIndex] = useState(0)
  const [picked, setPicked] = useState<number | null>(null)
  const current = questions[index]
  const answered = picked !== null

  const next = () => {
    setPicked(null)
    setIndex((index + 1) % questions.length)
  }

  return (
    <div
      className={cn(
        'bg-card rounded-2xl border p-6 shadow-sm sm:p-8',
        className,
      )}
    >
      <div className="flex items-center gap-2.5">
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: current.colour }}
        />
        <span className="text-sm font-semibold">{current.subject}</span>
        <span className="text-muted-foreground text-sm">
          · {current.domain}
        </span>
      </div>

      <p className="mt-4 text-lg font-medium text-pretty">{current.question}</p>

      <div className="mt-5 grid gap-2.5">
        {current.options.map((option, i) => {
          const correct = i === current.answer
          const chosen = i === picked
          return (
            <button
              key={option}
              type="button"
              disabled={answered}
              onClick={() => setPicked(i)}
              className={cn(
                'flex items-center gap-3 rounded-xl border p-3.5 text-left transition-colors',
                !answered && 'hover:border-primary/60 hover:bg-accent/60',
                answered && correct && 'border-primary bg-primary/10',
                answered &&
                  chosen &&
                  !correct &&
                  'border-destructive bg-destructive/10',
                answered && !correct && !chosen && 'opacity-55',
              )}
            >
              <span
                className={cn(
                  'flex size-7 shrink-0 items-center justify-center rounded-md border text-xs font-semibold',
                  answered &&
                    correct &&
                    'border-primary bg-primary text-primary-foreground',
                  answered &&
                    chosen &&
                    !correct &&
                    'border-destructive bg-destructive text-destructive-foreground',
                )}
              >
                {answered && correct ? (
                  <CheckIcon className="size-4" />
                ) : answered && chosen ? (
                  <XIcon className="size-4" />
                ) : (
                  letters[i]
                )}
              </span>
              <span className="flex-1">{option}</span>
            </button>
          )
        })}
      </div>

      <AnimatePresence initial={false}>
        {answered && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-5 flex flex-col gap-4 border-t pt-5 sm:flex-row sm:items-start sm:justify-between">
              <p className="text-muted-foreground text-sm text-pretty">
                <span className="text-foreground font-semibold">
                  {picked === current.answer ? 'Correct. ' : 'Not quite. '}
                </span>
                {current.why}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={next}
                className="shrink-0"
              >
                <RotateCcwIcon className="size-3.5" />
                Another
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
