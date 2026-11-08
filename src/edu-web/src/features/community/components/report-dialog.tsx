/**
 * Telling a teacher that a post needs looking at.
 *
 * The reasons are written as a sixteen year old would describe the problem,
 * not as a policy document names it. "Someone is being horrible" gets
 * pressed; "harassment or abusive conduct" does not.
 *
 * Nothing is hidden when a post is reported. The student is told an adult
 * will look, and that is all that happens: a report that removed a post
 * instantly would be a way for three friends to silence anyone.
 */

import { useEffect, useState } from 'react'
import { useAtom } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import { FlagIcon } from 'lucide-react'
import { reportPostAtom } from '@/data-acess/community'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

const REASONS = [
  { value: 'bullying', label: 'Someone is being horrible to a person' },
  { value: 'sexual', label: 'Sexual or inappropriate' },
  { value: 'hate', label: 'Hateful about a group of people' },
  { value: 'cheating', label: 'Sharing exam answers' },
  { value: 'contact', label: 'Personal details or a link' },
  { value: 'spam', label: 'Spam or advertising' },
  { value: 'worried', label: 'I am worried about this person' },
  { value: 'other', label: 'Something else' },
]

export const ReportDialog = ({
  postId,
  alreadyReported,
}: {
  postId: string
  alreadyReported: boolean
}) => {
  const [result, report] = useAtom(reportPostAtom)
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = async () => {
    setBusy(true)
    setError(null)
    try {
      await report({ postId, reason: reason ?? undefined, note })
    } finally {
      setBusy(false)
      setSent(true)
    }
  }

  /**
   * Only say it worked when it worked.
   *
   * The setter does not reject, so awaiting it and then showing "thank you"
   * said a teacher had been told whether or not one had. On a report button
   * that is worse than an error: a student who believes an adult is looking
   * stops looking for one themselves.
   */
  useEffect(() => {
    if (!sent || result.waiting) return
    if (result._tag === 'Failure') {
      const thrown = Cause.squash(result.cause)
      setError(
        thrown instanceof Error && thrown.message
          ? thrown.message
          : 'That did not send. Please try again.',
      )
    } else if (result._tag === 'Success') {
      setDone(true)
    }
    setSent(false)
    // result.cause is deliberately not a dependency: it only exists on a
    // Failure, so naming it does not typecheck on the union.
  }, [sent, result._tag, result.waiting])

  const close = () => {
    setOpen(false)
    // Left until the dialog has gone, so the content does not change shape
    // while it is fading out.
    setTimeout(() => {
      setDone(false)
      setReason(null)
      setNote('')
      setError(null)
    }, 200)
  }

  if (alreadyReported) {
    return (
      <span className="text-muted-foreground flex items-center gap-1 text-xs">
        <FlagIcon className="size-3" />
        Reported
      </span>
    )
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
      >
        <FlagIcon className="size-3" />
        Report
      </button>

      <Dialog
        open={open}
        onOpenChange={(next) => (next ? setOpen(true) : close())}
      >
        <DialogContent className="sm:max-w-md">
          {done ? (
            <>
              <DialogHeader>
                <DialogTitle>Thank you</DialogTitle>
                <DialogDescription>
                  A teacher will look at this. Nobody is told who reported it.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button onClick={close}>Close</Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>Report this post</DialogTitle>
                <DialogDescription>
                  A teacher will read it. The post stays up until they decide,
                  and the person who wrote it is not told who reported it.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-1.5">
                {REASONS.map((choice) => (
                  <button
                    key={choice.value}
                    type="button"
                    onClick={() => setReason(choice.value)}
                    aria-pressed={reason === choice.value}
                    className={cn(
                      'w-full rounded-md border px-3 py-2 text-left text-sm transition-colors',
                      reason === choice.value
                        ? 'border-primary bg-primary/5'
                        : 'hover:border-foreground/30',
                    )}
                  >
                    {choice.label}
                  </button>
                ))}
              </div>

              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Anything else a teacher should know (optional)"
                className="min-h-16 resize-none"
                maxLength={500}
              />

              {error ? (
                <p className="text-destructive text-sm" role="alert">
                  {error}
                </p>
              ) : null}

              <DialogFooter>
                <Button variant="ghost" onClick={close} disabled={busy}>
                  Cancel
                </Button>
                <Button onClick={() => void send()} disabled={busy || !reason}>
                  {busy ? 'Sending…' : 'Report'}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
