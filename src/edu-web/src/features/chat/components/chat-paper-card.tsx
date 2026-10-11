import { Result, useAtomRefresh, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { AlertCircleIcon, ChevronRightIcon, FileTextIcon, Loader2Icon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { paperAtom } from '@/data-acess/paper'
import { countQuestions, formatMarks } from '@/features/paper/paper-utils'
import { usePollWhile } from '@/hooks/use-poll-while'

/** A practice paper started from the chat: opens the exam page, then shows the result. */
export const ChatPaperCard = ({ projectId, paperId }: { projectId: string; paperId: string }) => {
  const atom = paperAtom(`${projectId}:${paperId}`)
  const result = useAtomValue(atom)
  const refresh = useAtomRefresh(atom)

  // Board papers are set by the worker; keep checking until they are ready
  const preparing = Result.isSuccess(result) && result.value.status === 'preparing'
  usePollWhile(preparing, refresh, { intervalMs: 5000, maxMs: 6 * 60_000 })

  if (!Result.isSuccess(result)) {
    return (
      <div className="flex max-w-2xl items-center gap-2 rounded-xl border bg-card p-4 text-sm text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin" />
        Loading paper…
      </div>
    )
  }
  const paper = result.value

  return (
    <div className="w-full max-w-2xl space-y-3 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2">
        <FileTextIcon className="size-5 text-primary" />
        <span className="font-semibold">{paper.title}</span>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {paper.status !== 'preparing' && paper.status !== 'failed' && (
          <Badge variant="secondary">{countQuestions(paper)} questions</Badge>
        )}
        <Badge variant="secondary">{formatMarks(paper.total_marks)} marks</Badge>
        <Badge variant="secondary">{paper.time_limit_minutes} minutes</Badge>
      </div>
      {paper.status === 'preparing' ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" />
          Setting your paper, usually one to three minutes…
        </div>
      ) : paper.status === 'failed' ? (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircleIcon className="size-4" />
          This paper could not be set. Ask me for another one.
        </div>
      ) : paper.status === 'submitted' && paper.result ? (
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-2xl font-bold">
            {formatMarks(paper.result.score)}/{formatMarks(paper.result.max_score)}
          </span>
          <Badge>{paper.result.grade}</Badge>
          <Button size="sm" variant="outline" asChild>
            <Link
              to="/dashboard/p/$projectId/paper/$paperId"
              params={{ projectId, paperId }}
            >
              View marked paper
              <ChevronRightIcon className="size-4" />
            </Link>
          </Button>
        </div>
      ) : (
        <Button asChild>
          <Link to="/dashboard/p/$projectId/paper/$paperId" params={{ projectId, paperId }}>
            Start paper
            <ChevronRightIcon className="size-4" />
          </Link>
        </Button>
      )}
    </div>
  )
}
