/**
 * The room a student shares with the rest of their own class.
 *
 * Pre-Medical XI and Pre-Engineering XI are different rooms, because they sit
 * different papers. There is no room selector: a student is in the one room
 * their grade and group put them in, and the server works that out from their
 * profile rather than taking it from the page.
 */

import { useState } from 'react'
import { Result, useAtomValue, useAtomSet } from '@effect-atom/atom-react'
import { MessageSquareIcon, Trash2Icon, UsersIcon } from 'lucide-react'
import type { CommunityPost } from '@/data-acess/community'
import {
  addPostAtom,
  communityRoomAtom,
  deletePostAtom,
} from '@/data-acess/community'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

const MAX_BODY = 2000

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

const Composer = ({
  parentId,
  placeholder,
  onDone,
}: {
  parentId?: string
  placeholder: string
  onDone?: () => void
}) => {
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const addPost = useAtomSet(addPostAtom)
  const tooLong = body.length > MAX_BODY

  const send = () => {
    const said = body.trim()
    if (!said || tooLong || sending) return
    setSending(true)
    addPost({ body: said, parentId })
    setBody('')
    setSending(false)
    onDone?.()
  }

  return (
    <div className="space-y-2">
      <Textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={placeholder}
        rows={parentId ? 2 : 3}
        onKeyDown={(event) => {
          // Enter sends, Shift+Enter breaks the line - a chat, not a form
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            send()
          }
        }}
      />
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            'text-xs',
            tooLong ? 'text-destructive' : 'text-muted-foreground',
          )}
        >
          {tooLong
            ? `${body.length - MAX_BODY} characters too many`
            : 'Enter to post, Shift+Enter for a new line'}
        </span>
        <Button size="sm" onClick={send} disabled={!body.trim() || tooLong}>
          {parentId ? 'Reply' : 'Post'}
        </Button>
      </div>
    </div>
  )
}

const Post = ({ post, depth = 0 }: { post: CommunityPost; depth?: number }) => {
  const [replying, setReplying] = useState(false)
  const deletePost = useAtomSet(deletePostAtom)

  return (
    <div className={cn(depth > 0 && 'ml-4 border-l pl-4 md:ml-6 md:pl-5')}>
      <div className="flex items-baseline gap-2 text-sm">
        <span className="font-medium">{post.author_name}</span>
        {post.is_mine && (
          <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
            you
          </Badge>
        )}
        <span className="text-xs text-muted-foreground">
          {when(post.created_at)}
        </span>
        {post.is_mine && (
          <button
            type="button"
            onClick={() => deletePost(post.id)}
            className="ml-auto text-muted-foreground hover:text-destructive"
            aria-label="Delete this post"
          >
            <Trash2Icon className="size-3.5" />
          </button>
        )}
      </div>

      {/* Plain text, deliberately. Anything a student types is shown as what
          they typed - no markdown, no HTML, nothing that could be made to
          render as something else in a classmate's browser. */}
      <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed">
        {post.body}
      </p>

      {depth === 0 && (
        <div className="mt-1.5">
          {replying ? (
            <div className="mt-2">
              <Composer
                parentId={post.id}
                placeholder={`Reply to ${post.author_name}…`}
                onDone={() => setReplying(false)}
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setReplying(true)}
              className="text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              Reply
            </button>
          )}
        </div>
      )}

      {post.replies.length > 0 && (
        <div className="mt-3 space-y-3">
          {post.replies.map((reply) => (
            <Post key={reply.id} post={reply} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export const CommunityPage = () => {
  const roomResult = useAtomValue(communityRoomAtom)

  if (!Result.isSuccess(roomResult)) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Loading your class…
      </div>
    )
  }

  const room = roomResult.value

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <MessageSquareIcon className="size-6" />
          {room.room_name}
        </h1>
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <UsersIcon className="size-3.5" />
          {room.member_count === 1
            ? 'You are the first one here'
            : `${room.member_count} students in your grade and group`}
        </p>
      </header>

      <Card>
        <CardContent className="pt-5">
          <Composer placeholder="Ask your class something, or share what helped you…" />
        </CardContent>
      </Card>

      {room.posts.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
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
