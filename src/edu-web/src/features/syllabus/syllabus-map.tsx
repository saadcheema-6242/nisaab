import { Result, useAtomValue } from '@effect-atom/atom-react'
import {
  ChevronRightIcon,
  ExternalLinkIcon,
  Loader2Icon,
  SearchIcon,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { assessmentForms, masteryLevel, masteryStyles } from './slo-labels'
import { SloSheet } from './slo-sheet'
import type {
  CurriculumTreeDto,
  DomainDto,
  SloDto,
} from '@/integrations/api/client'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { curriculumTreeAtom } from '@/data-acess/curriculum'
import { cn } from '@/lib/utils'
import { NewPaperDialog } from '@/features/paper/new-paper-dialog'

type Filter = 'all' | 'summative' | 'practical' | 'formative'

const filters: Array<{ value: Filter; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'summative', label: 'Examined' },
  { value: 'practical', label: 'Practical' },
  { value: 'formative', label: 'Not examined' },
]

const MasteryBar = ({ mastery }: { mastery?: number | null }) => {
  const level = masteryLevel(mastery)
  return (
    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
      <div
        className={cn('h-full rounded-full', masteryStyles[level].bar)}
        style={{ width: `${Math.round((mastery ?? 0) * 100)}%` }}
      />
    </div>
  )
}

const SloRow = ({ slo, onSelect }: { slo: SloDto; onSelect: () => void }) => {
  const level = masteryLevel(slo.mastery)
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className="flex w-full items-start gap-3 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-accent/60"
      >
        <span
          title={masteryStyles[level].label}
          className={cn(
            'mt-1.5 size-2.5 shrink-0 rounded-full',
            masteryStyles[level].dot,
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-xs font-medium text-muted-foreground">
              {slo.code}
            </span>
            {(slo.cognitive_levels ?? []).map((code) => (
              <span
                key={code}
                className="rounded bg-muted px-1 text-[10px] font-semibold text-muted-foreground"
              >
                {code}
              </span>
            ))}
            {slo.assessment_form !== 'summative' && (
              <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                {assessmentForms[slo.assessment_form].label}
              </Badge>
            )}
          </div>
          <p className="mt-0.5 line-clamp-2 text-sm">{slo.description}</p>
        </div>
      </button>
    </li>
  )
}

const DomainSection = ({
  domain,
  slos,
  defaultOpen,
  onSelect,
}: {
  domain: DomainDto
  slos: ReadonlyArray<SloDto>
  defaultOpen: boolean
  onSelect: (slo: SloDto) => void
}) => {
  // Keep FBISE's order; show a content-area heading when it changes
  const areas: Array<{ name: string; slos: Array<SloDto> }> = []
  for (const slo of slos) {
    const name = slo.content_area ?? domain.name
    const last = areas.at(-1)
    if (last && last.name === name) last.slos.push(slo)
    else areas.push({ name, slos: [slo] })
  }
  const showAreas = areas.length > 1 || areas[0]?.name !== domain.name

  return (
    <Collapsible defaultOpen={defaultOpen} className="rounded-xl border">
      <CollapsibleTrigger className="group flex w-full items-center gap-3 p-4 text-left">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-semibold text-primary">
          {domain.code}
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{domain.name}</div>
          <div className="text-xs text-muted-foreground">
            {domain.slo_count} SLOs · {domain.examined_count} examined
          </div>
        </div>
        <MasteryBar mastery={domain.mastery} />
        <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90" />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t px-2 pb-2">
        {areas.map((area, index) => (
          <div key={`${area.name}-${index}`}>
            {showAreas && (
              <div className="px-2 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {area.name}
              </div>
            )}
            <ul>
              {area.slos.map((slo) => (
                <SloRow key={slo.id} slo={slo} onSelect={() => onSelect(slo)} />
              ))}
            </ul>
          </div>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}

const SyllabusContent = ({
  tree,
  projectId,
  initialSloCode,
}: {
  tree: CurriculumTreeDto
  projectId: string
  initialSloCode?: string
}) => {
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  // Opened straight away when linked from the dashboard (?slo=P-11-B-05)
  const [selected, setSelected] = useState<SloDto | null>(
    () =>
      tree.domains
        .flatMap((domain) => domain.slos ?? [])
        .find((slo) => slo.code === initialSloCode) ?? null,
  )

  const domains = useMemo(() => {
    const q = query.trim().toLowerCase()
    return tree.domains
      .map((domain) => ({
        domain,
        slos: (domain.slos ?? []).filter(
          (slo) =>
            (filter === 'all' || slo.assessment_form === filter) &&
            (!q ||
              slo.code.toLowerCase().includes(q) ||
              slo.description.toLowerCase().includes(q) ||
              (slo.content_area ?? '').toLowerCase().includes(q)),
        ),
      }))
      .filter(({ slos }) => slos.length > 0)
  }, [tree, filter, query])

  const total = tree.domains.reduce((n, d) => n + d.slo_count, 0)
  const examined = tree.domains.reduce((n, d) => n + d.examined_count, 0)
  const searching = query.trim().length > 0 || filter !== 'all'

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <div>
        <h2 className="text-lg font-semibold">
          {tree.grade_subject.subject_name} syllabus map
        </h2>
        <p className="text-sm text-muted-foreground">
          {total} SLOs in {tree.domains.length} domains · {examined} can be
          asked in the annual exam · {tree.grade_subject.curriculum}
          {tree.grade_subject.source_url && (
            <>
              {' · '}
              <a
                href={tree.grade_subject.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 underline underline-offset-2"
              >
                FBISE Assessment Framework
                <ExternalLinkIcon className="size-3" />
              </a>
            </>
          )}
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <NewPaperDialog projectId={projectId} domains={tree.domains} />
        <div className="relative flex-1">
          <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search SLOs, e.g. projectile or B-05"
            className="pl-8"
          />
        </div>
        <div className="flex gap-1 overflow-x-auto">
          {filters.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              className={cn(
                'whitespace-nowrap rounded-full border px-3 py-1 text-sm transition-colors',
                filter === option.value
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'hover:bg-accent',
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {(['none', 'weak', 'developing', 'strong'] as const).map((level) => (
          <span key={level} className="flex items-center gap-1.5">
            <span className={cn('size-2 rounded-full', masteryStyles[level].dot)} />
            {masteryStyles[level].label}
          </span>
        ))}
        <span>K / U / A = Knowledge / Understanding / Application</span>
      </div>

      <div className="space-y-3">
        {domains.map(({ domain, slos }, index) => (
          <DomainSection
            // Re-mount when searching so matching domains open
            key={`${domain.code}-${searching}`}
            domain={domain}
            slos={slos}
            defaultOpen={searching || index === 0}
            onSelect={setSelected}
          />
        ))}
        {domains.length === 0 && (
          <p className="py-8 text-center text-muted-foreground">
            No SLOs match your search.
          </p>
        )}
      </div>

      <SloSheet
        projectId={projectId}
        slo={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}

type SyllabusMapProps = {
  projectId: string
  gradeSubjectId: string
  initialSloCode?: string
}

export const SyllabusMap = ({
  projectId,
  gradeSubjectId,
  initialSloCode,
}: SyllabusMapProps) => {
  const treeResult = useAtomValue(curriculumTreeAtom(gradeSubjectId))

  return Result.builder(treeResult)
    .onInitial(() => (
      <div className="flex items-center justify-center gap-2 p-12 text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin" />
        <span>Loading syllabus…</span>
      </div>
    ))
    .onFailure(() => (
      <div className="p-12 text-center text-destructive">
        Failed to load the syllabus
      </div>
    ))
    .onSuccess((tree) =>
      tree.grade_subject.status === 'coming_soon' ? (
        <div className="mx-auto max-w-xl p-12 text-center">
          <h2 className="text-lg font-semibold">
            {tree.grade_subject.subject_name} syllabus map is coming soon
          </h2>
          <p className="mt-2 text-muted-foreground">
            We are preparing the official FBISE SLO list for this subject. You
            can already chat with the tutor and upload your notes in the Study
            tab.
          </p>
        </div>
      ) : (
        <SyllabusContent
          tree={tree}
          projectId={projectId}
          initialSloCode={initialSloCode}
        />
      ),
    )
    .render()
}
