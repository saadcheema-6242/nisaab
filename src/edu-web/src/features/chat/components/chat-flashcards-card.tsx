import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  Loader2Icon,
  RotateCcwIcon,
  ThumbsUpIcon,
  UndoIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type {
  FlashcardAttemptDto,
  FlashcardDto,
} from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { flashcardGroupAtom, flashcardsAtom } from '@/data-acess/flashcard'
import {
  latestFlashcardAttemptAtom,
  submitFlashcardAttemptAtom,
} from '@/data-acess/flashcard-attempt'
import { cn } from '@/lib/utils'
import { FlashcardsDownload } from '@/components/downloads'

const FlipCard = ({
  card,
  flipped,
  onFlip,
}: {
  card: FlashcardDto
  flipped: boolean
  onFlip: () => void
}) => (
  <button
    type="button"
    onClick={onFlip}
    className="block w-full text-left [perspective:1000px]"
    aria-label={flipped ? 'Show question' : 'Show answer'}
  >
    <div
      className={cn(
        'grid transition-transform duration-500 [transform-style:preserve-3d]',
        flipped && '[transform:rotateY(180deg)]',
      )}
    >
      <div className="col-start-1 row-start-1 flex min-h-36 flex-col justify-center rounded-xl border bg-muted/40 p-4 [backface-visibility:hidden]">
        <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">
          Question
        </div>
        <MathText className="text-base font-medium">{card.question}</MathText>
        <div className="mt-2 text-xs text-muted-foreground">Tap to see the answer</div>
      </div>
      <div className="col-start-1 row-start-1 flex min-h-36 flex-col justify-center rounded-xl border border-primary/40 bg-primary/5 p-4 [backface-visibility:hidden] [transform:rotateY(180deg)]">
        <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">
          Answer
        </div>
        <MathText className="text-base">{card.answer}</MathText>
      </div>
    </div>
  </button>
)

/** Goes through the given cards once; reports whether each one was known. */
const Deck = ({
  cards,
  onDone,
  busy,
}: {
  cards: ReadonlyArray<FlashcardDto>
  onDone: (knew: Record<string, boolean>) => void
  busy: boolean
}) => {
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [knew, setKnew] = useState<Record<string, boolean>>({})
  const card = cards[index]

  const rate = (known: boolean) => {
    const next = { ...knew, [card.id]: known }
    setKnew(next)
    if (index === cards.length - 1) {
      onDone(next)
    } else {
      setIndex(index + 1)
      setFlipped(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Card {index + 1} of {cards.length}
        </span>
        <span>{Object.values(knew).filter(Boolean).length} known so far</span>
      </div>
      <FlipCard card={card} flipped={flipped} onFlip={() => setFlipped(!flipped)} />
      {flipped ? (
        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" disabled={busy} onClick={() => rate(false)}>
            <UndoIcon className="size-4" />
            Still learning
          </Button>
          <Button disabled={busy} onClick={() => rate(true)}>
            {busy ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <ThumbsUpIcon className="size-4" />
            )}
            Knew it
          </Button>
        </div>
      ) : (
        <Button variant="outline" className="w-full" onClick={() => setFlipped(true)}>
          Show answer
        </Button>
      )}
    </div>
  )
}

/** Flashcards the student studies inside the chat; the result is kept and counts for mastery. */
export const ChatFlashcardsCard = ({
  projectId,
  groupId,
}: {
  projectId: string
  groupId: string
}) => {
  const key = `${projectId}:${groupId}`
  const groupResult = useAtomValue(flashcardGroupAtom(key))
  const cardsResult = useAtomValue(flashcardsAtom(key))
  const attemptResult = useAtomValue(latestFlashcardAttemptAtom(key))
  const submit = useAtomSet(submitFlashcardAttemptAtom, { mode: 'promise' })
  const [mode, setMode] = useState<'auto' | 'study' | 'review'>('auto')
  const [fresh, setFresh] = useState<FlashcardAttemptDto | null>(null)
  const [busy, setBusy] = useState(false)
  const [round, setRound] = useState(0)

  const group = Result.isSuccess(groupResult) ? groupResult.value : null
  const cards = Result.isSuccess(cardsResult) ? cardsResult.value : null
  const saved = Result.isSuccess(attemptResult) ? attemptResult.value : null
  const attempt = fresh ?? saved

  const handleStudied = async (knew: Record<string, boolean>) => {
    setBusy(true)
    try {
      setFresh(await submit({ projectId, groupId, knew }))
      setMode('auto')
    } catch {
      toast.error('Could not save your progress, please try again')
    } finally {
      setBusy(false)
    }
  }

  const toReview =
    cards && attempt
      ? cards.filter((card) =>
          attempt.results.some((r) => r.flashcard_id === card.id && !r.knew),
        )
      : []

  const restart = (next: 'study' | 'review') => {
    setMode(next)
    setRound(round + 1)
  }

  return (
    <div className="w-full max-w-2xl space-y-3 rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{group?.name ?? 'Flashcards'}</span>
        {group?.slo_code && (
          <Badge variant="outline" className="font-mono">
            {group.slo_code}
          </Badge>
        )}
        {cards && (
          <span className="text-xs text-muted-foreground">{cards.length} cards</span>
        )}
        <div className="ml-auto">
          <FlashcardsDownload projectId={projectId} groupId={groupId} />
        </div>
      </div>

      {!cards || !Result.isSuccess(attemptResult) ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" />
          Loading flashcards…
        </div>
      ) : cards.length === 0 ? (
        <p className="text-sm text-muted-foreground">This set has no cards.</p>
      ) : mode === 'review' && toReview.length > 0 ? (
        <Deck
          key={`review-${round}`}
          cards={toReview}
          busy={false}
          onDone={() => setMode('auto')}
        />
      ) : mode === 'study' || !attempt ? (
        <Deck key={`study-${round}`} cards={cards} busy={busy} onDone={handleStudied} />
      ) : (
        <div className="space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-600">
              {attempt.known}/{attempt.total}
            </span>
            <span className="text-sm text-muted-foreground">
              cards known
              {toReview.length > 0 ? `, ${toReview.length} to review` : ' — all done!'}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {toReview.length > 0 && (
              <Button size="sm" onClick={() => restart('review')}>
                Review the {toReview.length} again
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => restart('study')}>
              <RotateCcwIcon className="size-4" />
              Study all again
            </Button>
            <Button size="sm" variant="ghost" asChild>
              <Link
                to="/dashboard/p/$projectId/f/$flashcardGroupId"
                params={{ projectId, flashcardGroupId: groupId }}
              >
                Open full set
                <ChevronRightIcon className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
