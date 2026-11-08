/**
 * The posts an administrator needs to look at.
 *
 * Ordered by how soon an adult is needed, not by time. A student who sounds
 * like they are in distress comes before a threat, a threat before spam, and
 * a post five students reported before one the model merely wondered about.
 * Sorting by newest would let the worst thing in the room sink as the room
 * gets busy, which is exactly backwards.
 *
 * Three states are kept apart, and the third is the one people get wrong:
 *
 *   flagged by the model
 *   reported by students
 *   never reviewed at all
 *
 * Never reviewed is not clean. A post written while Vertex was unreachable
 * has no verdict, and showing it as fine would be a quiet way for something
 * to sit unnoticed. It says "not reviewed" and it stays in the list.
 */

import { useState } from 'react'
import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import {
  CheckIcon,
  FlagIcon,
  LifeBuoyIcon,
  PaperclipIcon,
  ShieldAlertIcon,
  Trash2Icon,
} from 'lucide-react'
import type { ModerationItem } from '@/data-acess/community'
import {
  clearPostAtom,
  deleteAnyPostAtom,
  moderationQueueAtom,
} from '@/data-acess/community'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LoadingLine } from '@/components/ui/loading-line'

const when = (iso: string) =>
  new Date(iso).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })

const Stat = ({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone?: 'urgent' | 'normal'
}) => (
  <div className="rounded-lg border p-3">
    <p
      className={cn(
        'text-2xl font-semibold tabular-nums',
        tone === 'urgent' && value > 0 && 'text-destructive',
      )}
    >
      {value}
    </p>
    <p className="text-muted-foreground text-xs">{label}</p>
  </div>
)

const Item = ({ item }: { item: ModerationItem }) => {
  const remove = useAtomSet(deleteAnyPostAtom)
  const clear = useAtomSet(clearPostAtom)
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const act = async (what: 'delete' | 'clear') => {
    setBusy(true)
    try {
      if (what === 'delete') await remove(item.post_id)
      else await clear(item.post_id)
    } finally {
      setBusy(false)
      setConfirming(false)
    }
  }

  const distress = item.finding === 'self_harm'

  return (
    <Card
      className={cn(
        distress && 'border-sky-400 dark:border-sky-700',
        !distress && item.is_urgent && 'border-destructive',
      )}
    >
      <CardContent className="space-y-3 pt-5">
        <div className="flex flex-wrap items-center gap-2">
          {distress ? (
            <Badge className="gap-1 bg-sky-600 hover:bg-sky-600">
              <LifeBuoyIcon className="size-3" />
              Student may need help
            </Badge>
          ) : item.is_urgent ? (
            <Badge variant="destructive" className="gap-1">
              <ShieldAlertIcon className="size-3" />
              {item.finding_label}
            </Badge>
          ) : item.finding ? (
            <Badge variant="secondary">{item.finding_label}</Badge>
          ) : (
            <Badge variant="outline">Not reviewed</Badge>
          )}

          {item.report_count > 0 ? (
            <Badge variant="outline" className="gap-1">
              <FlagIcon className="size-3" />
              {item.report_count} reported
            </Badge>
          ) : null}

          {item.attachment_count > 0 ? (
            <Badge variant="outline" className="gap-1">
              <PaperclipIcon className="size-3" />
              {item.attachment_count}
            </Badge>
          ) : null}

          {item.warned_at ? (
            <span className="text-muted-foreground text-xs">
              author told {when(item.warned_at)}
            </span>
          ) : null}

          <span className="text-muted-foreground ml-auto text-xs">
            {item.room_name} · {when(item.created_at)}
          </span>
        </div>

        {/* The post in full. An administrator deciding whether to suspend
            somebody cannot work from an excerpt. */}
        <p className="bg-muted/40 rounded-md border p-3 text-sm whitespace-pre-wrap break-words">
          {item.body || (
            <em className="text-muted-foreground">No text, attachments only</em>
          )}
        </p>

        <div className="text-muted-foreground text-xs">
          <span className="text-foreground font-medium">
            {item.author_name}
          </span>
          {item.author_email ? ` · ${item.author_email}` : null}
          {item.confidence !== null && item.finding
            ? ` · model ${Math.round(item.confidence * 100)}% sure`
            : null}
        </div>

        {item.why ? (
          <p className="text-muted-foreground text-xs italic">“{item.why}”</p>
        ) : null}

        {item.reports.length > 0 ? (
          <ul className="space-y-1 border-l pl-3">
            {item.reports.map((report, index) => (
              <li key={index} className="text-muted-foreground text-xs">
                <span className="text-foreground">{report.reporter_name}</span>
                {report.reason ? ` · ${report.reason}` : null}
                {report.note ? ` — “${report.note}”` : null}
              </li>
            ))}
          </ul>
        ) : null}

        {distress ? (
          <p className="rounded-md border border-sky-300 bg-sky-50 p-3 text-xs dark:border-sky-900 dark:bg-sky-950/40">
            This post was not hidden and the student was not warned. They were
            sent a message asking them to talk to someone. Contact them or their
            class teacher today.
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {confirming ? (
            <>
              <span className="text-destructive self-center text-xs">
                Delete this post and its replies? This cannot be undone.
              </span>
              <Button
                size="sm"
                variant="destructive"
                disabled={busy}
                onClick={() => void act('delete')}
              >
                Yes, delete
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => setConfirming(false)}
              >
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void act('clear')}
              >
                <CheckIcon className="size-3.5" />
                <span className="ml-1.5">It is fine</span>
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => setConfirming(true)}
                className="text-destructive hover:text-destructive"
              >
                <Trash2Icon className="size-3.5" />
                <span className="ml-1.5">Delete</span>
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export const ModerationPanel = () => {
  const result = useAtomValue(moderationQueueAtom)

  if (!Result.isSuccess(result)) {
    return (
      <Card>
        <CardContent>
          <LoadingLine>Loading the class rooms</LoadingLine>
        </CardContent>
      </Card>
    )
  }

  const queue = result.value

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Class rooms</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat
            label="Need attention today"
            value={queue.urgent_count}
            tone="urgent"
          />
          <Stat label="Flagged by review" value={queue.flagged_count} />
          <Stat label="Reported by students" value={queue.reported_count} />
          <Stat label="Not reviewed" value={queue.unreviewed_count} />
        </CardContent>
      </Card>

      {queue.items.length === 0 ? (
        <Card>
          <CardContent className="text-muted-foreground py-10 text-center text-sm">
            Nothing waiting. Every post has been reviewed and none was flagged.
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {queue.items.map((item) => (
            <li key={item.post_id}>
              <Item item={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
