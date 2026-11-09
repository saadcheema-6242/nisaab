/**
 * Everything the student has made, across every subject.
 *
 * The per-project views answer "what is in Physics". This answers "where
 * is my work", which is the question a student actually asks a week
 * later, when they remember making a good quiz and not which workspace
 * they made it in.
 *
 * Tabs are All, then one per subject the student actually studies -
 * built from their own projects, so an ICS student is never offered a
 * Biology tab that could only ever be empty - and finally Shared, which
 * is where a public link is withdrawn.
 */

import { useState } from 'react'
import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  BrainIcon,
  CalendarRangeIcon,
  FileTextIcon,
  HistoryIcon,
  LayersIcon,
  ListChecksIcon,
  ScrollTextIcon,
} from 'lucide-react'
import { SharesPanel } from './shares-panel'
import type { HistoryItem, HistoryKind } from '@/data-acess/library'
import type { TabDef } from '@/components/ui/tab-strip'
import { historyAtom } from '@/data-acess/library'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingLine } from '@/components/ui/loading-line'
import { PageHeader } from '@/components/ui/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { TabPanel, TabStrip, useFirstOpened } from '@/components/ui/tab-strip'

/** What each kind is called, what it looks like, and where it opens. */
const KINDS: Record<
  HistoryKind,
  {
    label: string
    icon: React.ComponentType<{ className?: string }>
    path: string
  }
> = {
  quiz: { label: 'Quiz', icon: ListChecksIcon, path: 'q' },
  paper: { label: 'Paper', icon: ScrollTextIcon, path: 'paper' },
  flashcards: { label: 'Flashcards', icon: LayersIcon, path: 'f' },
  note: { label: 'Note', icon: FileTextIcon, path: 'n' },
  mind_map: { label: 'Mind map', icon: BrainIcon, path: 'm' },
  study_plan: {
    label: 'Study plan',
    icon: CalendarRangeIcon,
    path: 'study-plan',
  },
}

const when = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

/**
 * Where a row opens.
 *
 * Written out per kind rather than built as a string, because the router
 * types its own paths and params: a template literal compiles to
 * `string`, which it refuses, and the refusal is the point - a typo in a
 * path would otherwise be a dead link found by a student.
 */
const LinkTo = ({
  item,
  children,
  className,
}: {
  item: HistoryItem
  children: React.ReactNode
  className?: string
}) => {
  const p = { projectId: item.project_id }
  switch (item.kind) {
    case 'quiz':
      return (
        <Link
          to="/dashboard/p/$projectId/q/$quizId"
          params={{ ...p, quizId: item.id }}
          className={className}
        >
          {children}
        </Link>
      )
    case 'paper':
      return (
        <Link
          to="/dashboard/p/$projectId/paper/$paperId"
          params={{ ...p, paperId: item.id }}
          className={className}
        >
          {children}
        </Link>
      )
    case 'flashcards':
      return (
        <Link
          to="/dashboard/p/$projectId/f/$flashcardGroupId"
          params={{ ...p, flashcardGroupId: item.id }}
          className={className}
        >
          {children}
        </Link>
      )
    case 'note':
      return (
        <Link
          to="/dashboard/p/$projectId/n/$noteId"
          params={{ ...p, noteId: item.id }}
          className={className}
        >
          {children}
        </Link>
      )
    case 'mind_map':
      return (
        <Link
          to="/dashboard/p/$projectId/m/$mindMapId"
          params={{ ...p, mindMapId: item.id }}
          className={className}
        >
          {children}
        </Link>
      )
    case 'study_plan':
      // A plan hangs off the project; there is no id in its path.
      return (
        <Link
          to="/dashboard/p/$projectId/study-plan"
          params={p}
          className={className}
        >
          {children}
        </Link>
      )
  }
}

const Row = ({ item }: { item: HistoryItem }) => {
  const kind = KINDS[item.kind]
  const Icon = kind.icon
  return (
    <LinkTo item={item} className="group block rounded-lg outline-none">
      <div className="border-border/70 hover:border-border hover:bg-muted/40 group-focus-visible:ring-ring/45 flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors group-focus-visible:ring-[3px]">
        <div className="bg-accent text-accent-foreground grid size-9 shrink-0 place-items-center rounded-lg">
          <Icon className="size-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{item.name}</p>
          <p className="text-muted-foreground truncate text-xs">
            {kind.label}
            {item.subject_name ? ` · ${item.subject_name}` : ''}
            {item.count ? ` · ${item.count} items` : ''}
            {item.slo_code ? ` · ${item.slo_code}` : ''}
          </p>
        </div>
        {item.kind === 'paper' && item.status === 'submitted' && (
          <Badge variant="soft">Attempted</Badge>
        )}
        <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
          {when(item.created_at)}
        </span>
      </div>
    </LinkTo>
  )
}

const List = ({ items }: { items: Array<HistoryItem> }) => {
  if (items.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="text-muted-foreground py-10 text-center text-sm">
          Nothing here yet. Anything you make with the tutor - a quiz, a paper,
          flashcards, a mind map - appears here.
        </CardContent>
      </Card>
    )
  }
  return (
    <div className="space-y-2">
      {items.map((i) => (
        <Row key={`${i.kind}-${i.id}`} item={i} />
      ))}
    </div>
  )
}

export const HistoryPage = () => {
  const result = useAtomValue(historyAtom)
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
    { id: 'shared', label: 'Shared', hint: 'Links you have made' },
  ]

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-4 md:p-6">
      <PageHeader icon={HistoryIcon} title="History">
        Everything you have made with NISAAB, newest first. Opening one takes
        you back to where it lives.
      </PageHeader>

      {Result.builder(result)
        .onInitialOrWaiting(() => (
          <div className="space-y-2 pt-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ))
        .onFailure(() => (
          <Card className="border-destructive/25 bg-destructive/[0.04]">
            <CardContent className="text-muted-foreground py-8 text-center text-sm">
              We could not load your history. Reloading usually fixes it.
            </CardContent>
          </Card>
        ))
        .onSuccess((board) => (
          <>
            <TabStrip
              label="History"
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
            <TabPanel
              id="shared"
              active={tab === 'shared'}
              opened={opened.has('shared')}
            >
              <SharesPanel />
            </TabPanel>
          </>
        ))
        .render()}

      {!data && !Result.isFailure(result) && (
        <LoadingLine>Loading your history</LoadingLine>
      )}
    </div>
  )
}

export default HistoryPage
