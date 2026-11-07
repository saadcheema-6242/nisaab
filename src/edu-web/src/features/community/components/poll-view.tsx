/**
 * A poll in a class room.
 *
 * Results are shown straight away rather than hidden until you vote. This is
 * a class deciding which chapter is hardest, not an election, and a student
 * who only wants to know the answer should not have to add a vote they do
 * not mean in order to see it.
 */

import { CheckIcon } from 'lucide-react'
import type { CommunityPoll } from '@/data-acess/community'
import { cn } from '@/lib/utils'

export const PollView = ({
  poll,
  onVote,
  busy,
}: {
  poll: CommunityPoll
  onVote: (optionId: string) => void
  busy?: boolean
}) => (
  <div className="mt-3 space-y-2">
    <p className="text-sm font-medium">{poll.question}</p>

    <ul className="space-y-1.5">
      {poll.options.map((option) => (
        <li key={option.id}>
          <button
            type="button"
            disabled={busy}
            onClick={() => onVote(option.id)}
            aria-pressed={option.is_mine}
            className={cn(
              'relative w-full overflow-hidden rounded-md border px-3 py-2 text-left text-sm',
              'hover:border-foreground/30 transition-colors disabled:opacity-60',
              option.is_mine && 'border-primary',
            )}
          >
            {/* The bar sits behind the text rather than beside it, so a long
                option is not squeezed into half the width on a phone. */}
            <span
              aria-hidden
              className={cn(
                'absolute inset-y-0 left-0 transition-[width] duration-300',
                option.is_winning ? 'bg-primary/15' : 'bg-muted',
              )}
              style={{ width: `${option.percent}%` }}
            />
            <span className="relative flex items-center gap-2">
              {option.is_mine ? (
                <CheckIcon className="text-primary size-3.5 shrink-0" />
              ) : null}
              <span className="flex-1 break-words">{option.text}</span>
              <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
                {option.percent}%
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>

    <p className="text-muted-foreground text-xs">
      {poll.total_votes === 0
        ? 'No votes yet'
        : `${poll.total_votes} ${poll.total_votes === 1 ? 'vote' : 'votes'}`}
      {poll.has_voted ? ' · tap another option to change your answer' : ''}
    </p>
  </div>
)
