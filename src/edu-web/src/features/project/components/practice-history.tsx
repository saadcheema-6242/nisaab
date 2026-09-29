import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { format } from 'date-fns'
import {
  BrainCircuitIcon,
  ChevronRightIcon,
  FileTextIcon,
  ListChecksIcon,
  Loader2Icon,
} from 'lucide-react'
import type { PracticeHistoryItemDto } from '@/integrations/api/client'
import { practiceHistoryAtom } from '@/data-acess/quiz-attempt'
import { cn } from '@/lib/utils'

const kinds = {
  quiz: { icon: ListChecksIcon, label: 'Quiz' },
  flashcards: { icon: BrainCircuitIcon, label: 'Flashcards' },
  paper: { icon: FileTextIcon, label: 'Paper' },
} as const

const ItemLink = ({
  projectId,
  item,
  children,
}: {
  projectId: string
  item: PracticeHistoryItemDto
  children: React.ReactNode
}) => {
  const className =
    'flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50'
  if (item.kind === 'flashcards')
    return (
      <Link
        to="/dashboard/p/$projectId/f/$flashcardGroupId"
        params={{ projectId, flashcardGroupId: item.ref_id }}
        className={className}
      >
        {children}
      </Link>
    )
  if (item.kind === 'paper')
    return (
      <Link
        to="/dashboard/p/$projectId/paper/$paperId"
        params={{ projectId, paperId: item.ref_id }}
        className={className}
      >
        {children}
      </Link>
    )
  return (
    <Link
      to="/dashboard/p/$projectId/q/$quizId"
      params={{ projectId, quizId: item.ref_id }}
      className={className}
    >
      {children}
    </Link>
  )
}

/** Every finished quiz, flashcard run and paper, newest first; each retry is its own attempt. */
export const PracticeHistory = ({ projectId }: { projectId: string }) => {
  const historyResult = useAtomValue(practiceHistoryAtom(projectId))

  return (
    <div className="mx-auto w-full max-w-3xl space-y-3 p-4">
      <div>
        <h3 className="text-lg font-semibold">Practice history</h3>
        <p className="text-sm text-muted-foreground">
          Every quiz, flashcard set and paper you finished. Trying again saves a
          new attempt; earlier scores are kept.
        </p>
      </div>
      {Result.builder(historyResult)
        .onInitial(() => (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2Icon className="size-4 animate-spin" />
            <span>Loading your history…</span>
          </div>
        ))
        .onFailure(() => (
          <div className="text-destructive">Could not load your history</div>
        ))
        .onSuccess((items) =>
          items.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              Nothing yet. Ask the tutor for a quiz, flashcards or a practice
              paper.
            </div>
          ) : (
            <ul className="space-y-2">
              {items.map((item) => {
                const kind =
                  item.kind in kinds
                    ? kinds[item.kind as keyof typeof kinds]
                    : kinds.quiz
                const Icon = kind.icon
                const ratio = item.max_score ? item.score / item.max_score : 0
                return (
                  <li key={item.id}>
                    <ItemLink projectId={projectId} item={item}>
                      <Icon className="size-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium">
                          {item.title}
                          <span className="font-normal text-muted-foreground">
                            {' '}
                            · Attempt {item.number}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {kind.label} ·{' '}
                          {format(new Date(item.created_at), 'd MMM, h:mm a')}
                        </div>
                      </div>
                      <span
                        className={cn(
                          'shrink-0 font-semibold tabular-nums',
                          ratio >= 0.8
                            ? 'text-emerald-600'
                            : ratio >= 0.5
                              ? 'text-amber-600'
                              : 'text-red-600',
                        )}
                      >
                        {item.score}/{item.max_score}
                      </span>
                      <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" />
                    </ItemLink>
                  </li>
                )
              })}
            </ul>
          ),
        )
        .render()}
    </div>
  )
}
