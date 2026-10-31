import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { format } from 'date-fns'
import {
  BrainCircuitIcon,
  CalendarDaysIcon,
  ChevronRightIcon,
  DownloadIcon,
  FileTextIcon,
  ListChecksIcon,
  Loader2Icon,
  NetworkIcon,
  StickyNoteIcon,
} from 'lucide-react'
import { useState } from 'react'
import type { PracticeHistoryItemDto } from '@/integrations/api/client'
import {
  FlashcardsDownload,
  MindMapDownload,
  NoteDownload,
  PaperDownload,
  QuizDownload,
} from '@/components/downloads'
import { Button } from '@/components/ui/button'
import { practiceHistoryAtom } from '@/data-acess/quiz-attempt'
import { cn } from '@/lib/utils'

const kinds = {
  quiz: { icon: ListChecksIcon, label: 'Quiz' },
  flashcards: { icon: BrainCircuitIcon, label: 'Flashcards' },
  paper: { icon: FileTextIcon, label: 'Paper' },
  mind_map: { icon: NetworkIcon, label: 'Mind map' },
  note: { icon: StickyNoteIcon, label: 'Note' },
  study_plan: { icon: CalendarDaysIcon, label: 'Study plan' },
} as const

/**
 * The same download menu the item's own page offers.
 *
 * It only mounts once asked for: each menu loads the item's data, and a history
 * of thirty attempts would otherwise fire sixty requests the moment the list
 * opened. The click that arms it also opens it, so it still feels like one tap.
 */
const HistoryDownload = ({
  projectId,
  item,
}: {
  projectId: string
  item: PracticeHistoryItemDto
}) => {
  const [armed, setArmed] = useState(false)

  // A study plan has no printable form of its own yet
  if (item.kind === 'study_plan') return null

  if (!armed) {
    return (
      <Button
        size="icon"
        variant="ghost"
        aria-label={`Download ${item.title}`}
        onClick={() => setArmed(true)}
      >
        <DownloadIcon className="size-4" />
      </Button>
    )
  }
  const shared = { projectId, iconOnly: true, autoOpen: true } as const
  if (item.kind === 'flashcards')
    return <FlashcardsDownload {...shared} groupId={item.ref_id} />
  if (item.kind === 'paper')
    return <PaperDownload {...shared} paperId={item.ref_id} />
  if (item.kind === 'mind_map')
    return <MindMapDownload {...shared} mindMapId={item.ref_id} />
  if (item.kind === 'note')
    return <NoteDownload {...shared} noteId={item.ref_id} />
  return <QuizDownload {...shared} quizId={item.ref_id} />
}

const ItemLink = ({
  projectId,
  item,
  children,
}: {
  projectId: string
  item: PracticeHistoryItemDto
  children: React.ReactNode
}) => {
  const className = 'flex flex-1 items-center gap-3 p-3 min-w-0'
  if (item.kind === 'mind_map')
    return (
      <Link
        to="/dashboard/p/$projectId/m/$mindMapId"
        params={{ projectId, mindMapId: item.ref_id }}
        className={className}
      >
        {children}
      </Link>
    )
  if (item.kind === 'note')
    return (
      <Link
        to="/dashboard/p/$projectId/n/$noteId"
        params={{ projectId, noteId: item.ref_id }}
        className={className}
      >
        {children}
      </Link>
    )
  if (item.kind === 'study_plan')
    return (
      <Link
        to="/dashboard/p/$projectId/study-plan"
        params={{ projectId }}
        className={className}
      >
        {children}
      </Link>
    )
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
          Everything the tutor has made for you, newest first. Attempts keep their
          score, and trying again saves a new attempt rather than replacing it.
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
                // Only attempted items carry a score; a mind map or a note has none
                const score = item.score ?? null
                const maxScore = item.max_score ?? null
                const attempt = item.number ?? null
                const scored = score !== null && maxScore !== null
                const ratio = scored && maxScore ? score / maxScore : 0
                return (
                  <li
                    key={item.id}
                    className="flex items-center gap-1 rounded-lg border pr-2 transition-colors hover:bg-accent/50"
                  >
                    <ItemLink projectId={projectId} item={item}>
                      <Icon className="size-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium">
                          {item.title}
                          {attempt !== null && (
                            <span className="font-normal text-muted-foreground">
                              {' '}
                              · Attempt {attempt}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {kind.label} ·{' '}
                          {format(new Date(item.created_at), 'd MMM, h:mm a')}
                        </div>
                      </div>
                      {scored ? (
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
                          {score}/{maxScore}
                        </span>
                      ) : (
                        <span className="text-muted-foreground shrink-0 text-xs">
                          Not attempted
                        </span>
                      )}
                      <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground" />
                    </ItemLink>
                    <HistoryDownload projectId={projectId} item={item} />
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
