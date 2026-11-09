/**
 * The links this student has made, and the way to withdraw one.
 *
 * Sharing is the only thing in NISAAB that makes a student's work
 * readable by strangers, so there has to be one place that answers
 * "what have I made public" without hunting through every quiz. This is
 * it, and revoking is one press.
 *
 * Revoking is confirmed, because the link may already be in a group
 * chat and the student cannot un-send it: the consequence of the mistake
 * is that a friend's link stops working with no explanation.
 */

import { useState } from 'react'
import { Result, useAtom, useAtomValue } from '@effect-atom/atom-react'
import {
  CheckIcon,
  CopyIcon,
  ExternalLinkIcon,
  Link2OffIcon,
  ListChecksIcon,
  ScrollTextIcon,
} from 'lucide-react'
import type { Share } from '@/data-acess/shares'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useConfirmationDialog } from '@/components/confirmation-dialog'
import { mySharesAtom, revokeShareAtom, shareUrl } from '@/data-acess/shares'

const KIND = {
  quiz: { label: 'Quiz', icon: ListChecksIcon },
  paper: { label: 'Paper', icon: ScrollTextIcon },
} as const

const Row = ({ share }: { share: Share }) => {
  const [, revoke] = useAtom(revokeShareAtom)
  const confirm = useConfirmationDialog()
  const [copied, setCopied] = useState(false)
  const url = shareUrl(share)
  const meta = KIND[share.kind]
  const Icon = meta.icon

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* the link is shown in full below, so there is still a way through */
    }
  }

  const withdraw = async () => {
    const ok = await confirm.open({
      title: 'Withdraw this link?',
      description:
        'Anyone who already has it will stop being able to open it, and they will not be told why. The ' +
        meta.label.toLowerCase() +
        ' itself is not affected, and you can share it again later.',
      confirmLabel: 'Withdraw',
      variant: 'destructive',
    })
    if (ok) revoke(share.id)
  }

  return (
    <div className="border-border/70 flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5">
      <div className="bg-accent text-accent-foreground grid size-9 shrink-0 place-items-center rounded-lg">
        <Icon className="size-4.5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {share.title ?? 'Untitled'}
        </p>
        <p className="text-muted-foreground truncate font-mono text-xs">
          {url}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button variant="ghost" size="sm" onClick={() => void copy()}>
          {copied ? <CheckIcon /> : <CopyIcon />}
          {copied ? 'Copied' : 'Copy'}
        </Button>
        <Button variant="ghost" size="icon-sm" asChild>
          <a
            href={share.path}
            target="_blank"
            rel="noreferrer"
            aria-label="Open the link"
          >
            <ExternalLinkIcon />
          </a>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={() => void withdraw()}
        >
          <Link2OffIcon /> Withdraw
        </Button>
      </div>
    </div>
  )
}

export const SharesPanel = () => {
  const result = useAtomValue(mySharesAtom)

  return Result.builder(result)
    .onInitialOrWaiting(() => (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    ))
    .onFailure(() => (
      <Card className="border-destructive/25 bg-destructive/[0.04]">
        <CardContent className="text-muted-foreground py-8 text-center text-sm">
          We could not load your links just now.
        </CardContent>
      </Card>
    ))
    .onSuccess((shares) =>
      shares.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="text-muted-foreground py-10 text-center text-sm">
            You have not shared anything yet. Open a quiz or a paper and press
            Share to make a link anyone can read, with the answers shown.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {shares.map((s) => (
            <Row key={s.id} share={s} />
          ))}
        </div>
      ),
    )
    .render()
}
