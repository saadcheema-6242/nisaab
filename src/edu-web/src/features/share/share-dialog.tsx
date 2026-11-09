/**
 * Making a link, and copying it.
 *
 * The dialog does the one thing people actually came for - put the URL
 * on the clipboard - and says plainly what the link does, because
 * "share" means different things in different products and the
 * difference matters here: this one cannot be attempted.
 *
 * Pressing Share twice returns the same link rather than minting a
 * second. The server decides that; this only has to not assume
 * otherwise.
 */

import { useEffect, useState } from 'react'
import { useAtom } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import { CheckIcon, CopyIcon, Share2Icon } from 'lucide-react'
import type { Share } from '@/data-acess/shares'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { createShareAtom, shareUrl } from '@/data-acess/shares'

export const ShareDialog = ({
  open,
  onOpenChange,
  kind,
  targetId,
  title,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  kind: 'quiz' | 'paper'
  targetId: string
  title?: string
}) => {
  const [result, create] = useAtom(createShareAtom)
  const [share, setShare] = useState<Share | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [asked, setAsked] = useState(false)

  // Ask for the link as the dialog opens, so by the time the person has
  // read the sentence the URL is already there to copy.
  useEffect(() => {
    if (!open || asked) return
    setAsked(true)
    setError(null)
    create({ kind, target_id: targetId, title })
  }, [open, asked, create, kind, targetId, title])

  useEffect(() => {
    if (!open) {
      setAsked(false)
      setShare(null)
      setCopied(false)
      setError(null)
    }
  }, [open])

  // The setter does not reject, so the outcome is read from the Result.
  useEffect(() => {
    if (!asked || result.waiting) return
    if (result._tag === 'Success') {
      setShare(result.value)
    } else if (result._tag === 'Failure') {
      const thrown: unknown = Cause.squash(result.cause)
      setError(
        thrown instanceof Error && thrown.message
          ? thrown.message
          : 'Could not make a link just now.',
      )
    }
  }, [asked, result])

  const url = share ? shareUrl(share) : ''

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // Clipboard access can be refused; the field is selectable, so
      // there is still a way through rather than a dead end.
      setError('Could not copy. Select the link and copy it by hand.')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2Icon className="size-4.5" />
            Share this {kind}
          </DialogTitle>
          <DialogDescription>
            Anyone with this link can read it, with the answers and explanations
            shown. They cannot attempt it, and they do not need an account.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <p className="border-destructive/25 bg-destructive/10 text-destructive rounded-lg border p-3 text-sm">
            {error}
          </p>
        ) : share ? (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                readOnly
                value={url}
                onFocus={(e) => e.currentTarget.select()}
                className="font-mono text-xs"
                aria-label="The link to share"
              />
              <Button onClick={() => void copy()} className="shrink-0">
                {copied ? <CheckIcon /> : <CopyIcon />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <p className="text-muted-foreground text-xs leading-relaxed">
              You can withdraw this link at any time from{' '}
              <span className="text-foreground font-medium">History</span> →{' '}
              <span className="text-foreground font-medium">Shared</span>. The{' '}
              {kind} itself is not affected.
            </p>
          </div>
        ) : (
          <p className="text-muted-foreground flex items-center gap-2 py-4 text-sm">
            <Spinner className="size-4" /> Making the link…
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
