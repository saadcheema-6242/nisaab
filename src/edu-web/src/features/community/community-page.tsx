/**
 * The room a student shares with the rest of their own class.
 *
 * Pre-Medical XI and Pre-Engineering XI are different rooms, because they sit
 * different papers. There is no room selector: a student is in the one room
 * their grade and group put them in, and the server works that out from their
 * profile rather than taking it from the page.
 *
 * Nothing here shows that a post was flagged, how many people reported it, or
 * what the model thought. A room that displays its own moderation turns into
 * an argument about the moderation, and a student who can see what gets
 * flagged can work out how to word things so they are not.
 */

import { useState } from 'react'
import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import {
  HeartIcon,
  MessageSquareIcon,
  Trash2Icon,
  TriangleAlertIcon,
  UsersIcon,
  XIcon,
} from 'lucide-react'
import { AttachmentList } from './components/attachment-view'
import { Composer } from './components/composer'
import { PollView } from './components/poll-view'
import { ReportDialog } from './components/report-dialog'
import { RoomSwitcher } from './components/room-switcher'
import type { CommunityPost, CommunityWarning } from '@/data-acess/community'
import {
  communityRoomAtom,
  deletePostAtom,
  dismissWarningsAtom,
  voteAtom,
} from '@/data-acess/community'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LoadingLine } from '@/components/ui/loading-line'
import { PageHeader } from '@/components/ui/page-header'

/** When it was said, the way a person would say it. */
const when = (iso: string) => {
  const then = new Date(iso)
  const minutes = Math.round((Date.now() - then.getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days} d ago`
  return then.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

/**
 * A message from moderation, for the author alone.
 *
 * Two shapes, and the difference matters more than anything else on this
 * page. A warning is a telling-off and looks like one. An offer of help to a
 * student who sounded like they were struggling must not: the first thing
 * they read should not feel like being in trouble.
 */
const WarningBanner = ({
  warning,
  onDismiss,
}: {
  warning: CommunityWarning
  onDismiss: () => void
}) => (
  <div
    role="status"
    className={cn(
      'flex items-start gap-3 rounded-lg border p-4',
      warning.is_support
        ? 'border-sky-300 bg-sky-50 dark:border-sky-900 dark:bg-sky-950/40'
        : 'border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40',
    )}
  >
    {warning.is_support ? (
      <HeartIcon className="mt-0.5 size-4 shrink-0 text-sky-600 dark:text-sky-400" />
    ) : (
      <TriangleAlertIcon className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
    )}
    <p className="flex-1 text-sm">{warning.message}</p>
    <button
      type="button"
      onClick={onDismiss}
      aria-label="Dismiss"
      className="text-muted-foreground hover:text-foreground shrink-0"
    >
      <XIcon className="size-4" />
    </button>
  </div>
)

const Post = ({ post, depth = 0 }: { post: CommunityPost; depth?: number }) => {
  const [replying, setReplying] = useState(false)
  const [busy, setBusy] = useState(false)
  const deletePost = useAtomSet(deletePostAtom)
  const vote = useAtomSet(voteAtom)

  const onVote = async (optionId: string) => {
    setBusy(true)
    try {
      await vote({ postId: post.id, optionId })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-medium">{post.author_name}</span>
        {/* Beside the name, never instead of it. Replacing the name would
            hide who actually wrote the post, and any student could then
            call themselves Admin and be indistinguishable from one. */}
        {post.author_role && (
          <Badge
            variant={post.author_role === 'admin' ? 'default' : 'secondary'}
            className="h-5 px-1.5 text-[11px] capitalize"
          >
            {post.author_role}
          </Badge>
        )}
        <span className="text-muted-foreground text-xs">
          {when(post.created_at)}
        </span>
        {post.is_mine ? (
          <button
            type="button"
            onClick={() => void deletePost(post.id)}
            className="text-muted-foreground hover:text-destructive ml-auto"
            aria-label="Delete this post"
          >
            <Trash2Icon className="size-3.5" />
          </button>
        ) : null}
      </div>

      {post.body ? (
        <p className="mt-1 text-sm whitespace-pre-wrap break-words">
          {post.body}
        </p>
      ) : null}

      <AttachmentList files={post.attachments} />

      {post.poll ? (
        <PollView poll={post.poll} onVote={onVote} busy={busy} />
      ) : null}

      <div className="mt-2 flex items-center gap-4">
        {depth === 0 && !replying ? (
          <button
            type="button"
            onClick={() => setReplying(true)}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            Reply
          </button>
        ) : null}
        {!post.is_mine ? (
          <ReportDialog
            postId={post.id}
            alreadyReported={post.reported_by_me}
          />
        ) : null}
      </div>

      {replying ? (
        <div className="mt-3">
          <Composer
            parentId={post.id}
            autoFocus
            placeholder={`Reply to ${post.author_name}…`}
            onDone={() => setReplying(false)}
          />
        </div>
      ) : null}

      {post.replies.length > 0 ? (
        <ul className="mt-3 space-y-3 border-l pl-4">
          {post.replies.map((reply) => (
            <li key={reply.id}>
              <Post post={reply} depth={depth + 1} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

export const CommunityPage = () => {
  const roomResult = useAtomValue(communityRoomAtom)
  const dismiss = useAtomSet(dismissWarningsAtom)

  if (Result.isFailure(roomResult)) {
    return (
      <div className="mx-auto w-full max-w-3xl p-6">
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm font-medium">Your class room is not ready</p>
            <p className="text-muted-foreground mt-1 text-sm">
              Finish choosing your class and group, and this is where the rest
              of your year will be.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!Result.isSuccess(roomResult)) {
    return <LoadingLine>Loading your class</LoadingLine>
  }

  const room = roomResult.value

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 p-4 md:p-6">
      <PageHeader icon={MessageSquareIcon} title={room.room_name}>
        <span className="flex items-center gap-1.5">
          <UsersIcon className="size-3.5 shrink-0" />
          {room.member_count === 1
            ? 'You are the first one here'
            : `${room.member_count} students in your grade and group`}
        </span>
      </PageHeader>

      <RoomSwitcher />

      {room.warnings.map((warning) => (
        <WarningBanner
          key={warning.post_id}
          warning={warning}
          onDismiss={() => void dismiss()}
        />
      ))}

      <Card>
        <CardContent className="pt-5">
          <Composer placeholder="Ask your class something, or share what helped you…" />
          {/* Only shown as it starts to matter. A counter at 40 of 40 is
              noise; one at 3 left is worth knowing before you type. */}
          {room.posts_left_today <= 5 ? (
            <p className="text-muted-foreground mt-2 text-xs">
              {room.posts_left_today === 0
                ? 'You have used your posts for today. More tomorrow.'
                : `${room.posts_left_today} posts left today`}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {room.posts.length === 0 ? (
        <Card>
          <CardContent className="text-muted-foreground py-10 text-center text-sm">
            Nothing here yet. Ask the first question.
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {room.posts.map((post) => (
            <li key={post.id}>
              <Card>
                <CardContent className="pt-5">
                  <Post post={post} />
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default CommunityPage
