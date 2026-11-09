/**
 * Everything the student has uploaded, across every subject.
 *
 * The companion to History: that page is what NISAAB made, this is what
 * the student brought. Separated because they are found by different
 * questions - "where is the quiz I made" and "where is that past paper
 * I uploaded" - and a single list mixing them answers neither well.
 *
 * A document's processing state is shown, because an upload that is
 * still being read cannot be asked about yet, and a student who is not
 * told that assumes the tutor is ignoring their file.
 */

import { useState } from 'react'
import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { FileIcon, LibraryIcon } from 'lucide-react'
import type { DocumentItem } from '@/data-acess/library'
import type { TabDef } from '@/components/ui/tab-strip'
import { documentsAtom } from '@/data-acess/library'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { TabPanel, TabStrip, useFirstOpened } from '@/components/ui/tab-strip'

/** Bytes, said the way a person would. */
const size = (bytes: number) => {
  if (!bytes) return ''
  const mb = bytes / 1_048_576
  return mb >= 1
    ? `${mb.toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

const when = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
      })
    : ''

const STATE: Record<
  string,
  { label: string; variant: 'soft' | 'secondary' | 'destructive' }
> = {
  uploaded: { label: 'Being read', variant: 'secondary' },
  processing: { label: 'Being read', variant: 'secondary' },
  processed: { label: 'Ready', variant: 'soft' },
  failed: { label: 'Could not be read', variant: 'destructive' },
}

const Row = ({ doc }: { doc: DocumentItem }) => {
  const state = STATE[doc.status] ?? {
    label: doc.status,
    variant: 'secondary' as const,
  }
  return (
    <Link
      to="/dashboard/p/$projectId/d/$documentId"
      params={{ projectId: doc.project_id, documentId: doc.id }}
      className="group block rounded-lg outline-none"
    >
      <div className="border-border/70 hover:border-border hover:bg-muted/40 group-focus-visible:ring-ring/45 flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors group-focus-visible:ring-[3px]">
        <div className="bg-accent text-accent-foreground grid size-9 shrink-0 place-items-center rounded-lg">
          <FileIcon className="size-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{doc.file_name}</p>
          <p className="text-muted-foreground truncate text-xs">
            {doc.subject_name ?? doc.project_name ?? 'My projects'}
            {doc.file_size ? ` · ${size(doc.file_size)}` : ''}
            {doc.file_type ? ` · ${doc.file_type.toUpperCase()}` : ''}
          </p>
        </div>
        {/* "Ready" is the quiet one, so it does not shout on every row. */}
        {doc.status !== 'processed' && (
          <Badge variant={state.variant}>{state.label}</Badge>
        )}
        <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
          {when(doc.uploaded_at)}
        </span>
      </div>
    </Link>
  )
}

const List = ({ items }: { items: Array<DocumentItem> }) => {
  if (items.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="text-muted-foreground py-10 text-center text-sm">
          Nothing uploaded yet. Add a past paper, a chapter or your own notes
          inside a subject, and the tutor can answer from it.
        </CardContent>
      </Card>
    )
  }
  return (
    <div className="space-y-2">
      {items.map((d) => (
        <Row key={d.id} doc={d} />
      ))}
    </div>
  )
}

export const LibraryPage = () => {
  const result = useAtomValue(documentsAtom)
  const [tab, setTab] = useState('all')
  const opened = useFirstOpened(tab)
  const data = Result.isSuccess(result) ? result.value : null

  const tabs: Array<TabDef<string>> = [
    { id: 'all', label: 'All', badge: data?.items.length },
    ...(data?.subjects ?? []).map((s) => ({
      id: s.code,
      label: s.name,
      badge: data?.items.filter((i) => i.subject_code === s.code).length,
    })),
  ]

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-4 md:p-6">
      <PageHeader icon={LibraryIcon} title="Library">
        Every file you have uploaded. The tutor reads from these when it
        answers, so a past paper here is a past paper it can quote.
      </PageHeader>

      {Result.builder(result)
        .onInitialOrWaiting(() => (
          <div className="space-y-2 pt-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ))
        .onFailure(() => (
          <Card className="border-destructive/25 bg-destructive/[0.04]">
            <CardContent className="text-muted-foreground py-8 text-center text-sm">
              We could not load your library. Reloading usually fixes it.
            </CardContent>
          </Card>
        ))
        .onSuccess((board) => (
          <>
            <TabStrip
              label="Library"
              tabs={tabs}
              active={tab}
              onSelect={setTab}
            />
            <TabPanel
              id="all"
              active={tab === 'all'}
              opened={opened.has('all')}
            >
              <List items={board.items} />
            </TabPanel>
            {board.subjects.map((s) => (
              <TabPanel
                key={s.code}
                id={s.code}
                active={tab === s.code}
                opened={opened.has(s.code)}
              >
                <List
                  items={board.items.filter((i) => i.subject_code === s.code)}
                />
              </TabPanel>
            ))}
          </>
        ))
        .render()}
    </div>
  )
}

export default LibraryPage
