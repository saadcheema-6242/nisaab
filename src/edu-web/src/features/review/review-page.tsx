import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { CheckIcon, Loader2Icon, XIcon } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import type { ContentItemDto } from '@/integrations/api/client'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Textarea } from '@/components/ui/textarea'
import { curriculumTreeAtom, gradeSubjectsAtom } from '@/data-acess/curriculum'
import {
  reviewItemAtom,
  reviewItemsAtom,
  reviewSummaryAtom,
  reviewerStateAtom,
} from '@/data-acess/review'
import { gradeName } from '@/lib/subjects'
import { cn } from '@/lib/utils'

type Payload = Record<string, any>
type Status = ContentItemDto['review_status']

const ALL = 'all'
const kinds = [
  { value: ALL, label: 'All types' },
  { value: 'explainer', label: 'Explainers' },
  { value: 'mcq', label: 'MCQs' },
  { value: 'srq', label: 'SRQs' },
]
const statuses = [
  { value: 'draft', label: 'To review' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'approved', label: 'Approved' },
  { value: ALL, label: 'All' },
]
const statusStyles: Record<Status, string> = {
  draft: 'bg-muted text-muted-foreground',
  approved: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  rejected: 'bg-red-500/15 text-red-700 dark:text-red-400',
}

const McqView = ({ payload }: { payload: Payload }) => (
  <div className="space-y-2">
    <MathText className="font-medium">{payload.question_text ?? ''}</MathText>
    <ul className="grid gap-1">
      {(['a', 'b', 'c', 'd'] as const).map((key) => (
        <li
          key={key}
          className={cn(
            'flex gap-2 rounded border px-2 py-1',
            payload.correct_option === key &&
              'border-emerald-500 bg-emerald-500/10',
          )}
        >
          <span className="font-semibold uppercase">{key}.</span>
          <MathText>{payload[`option_${key}`] ?? ''}</MathText>
        </li>
      ))}
    </ul>
    {payload.explanation && (
      <div className="text-muted-foreground">
        <span className="font-medium">Explanation: </span>
        <MathText>{payload.explanation}</MathText>
      </div>
    )}
  </div>
)

const SrqView = ({ payload }: { payload: Payload }) => (
  <div className="space-y-2">
    <MathText className="font-medium">{payload.question ?? ''}</MathText>
    <div>
      <div className="font-medium">Marking points ({payload.marks} marks)</div>
      <ol className="ml-5 list-decimal">
        {(payload.rubric ?? []).map((point: Payload, index: number) => (
          <li key={index}>
            <MathText>{`${point.point} [${point.marks}]`}</MathText>
          </li>
        ))}
      </ol>
    </div>
    <div className="rounded bg-muted/60 p-2">
      <div className="font-medium">Model answer</div>
      <MathText>{payload.model_answer ?? ''}</MathText>
    </div>
  </div>
)

const ItemCard = ({ item }: { item: ContentItemDto }) => {
  const reviewItem = useAtomSet(reviewItemAtom, { mode: 'promise' })
  const [status, setStatus] = useState<Status>(item.review_status)
  const [note, setNote] = useState(item.review_note ?? '')
  const [rejecting, setRejecting] = useState(false)
  const [saving, setSaving] = useState(false)

  const save = async (next: Status, reviewNote?: string) => {
    setSaving(true)
    try {
      await reviewItem({
        itemId: item.id,
        gradeSubjectId: item.grade_subject_id,
        review_status: next,
        review_note: reviewNote || undefined,
      })
      setStatus(next)
      setRejecting(false)
    } catch {
      toast.error('Could not save the review')
    } finally {
      setSaving(false)
    }
  }

  const payload = item.payload as Payload
  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant="outline">{item.kind.toUpperCase()}</Badge>
        {payload.cognitive_level && (
          <Badge variant="secondary">Level {payload.cognitive_level}</Badge>
        )}
        <span
          className={cn('rounded px-2 py-0.5 text-xs', statusStyles[status])}
        >
          {status === 'draft' ? 'Not reviewed' : status}
        </span>
      </div>

      {item.kind === 'explainer' && (
        <div className="space-y-1">
          <div className="font-semibold">{payload.title}</div>
          <MathText className="prose prose-sm dark:prose-invert max-w-none">
            {payload.content ?? ''}
          </MathText>
        </div>
      )}
      {item.kind === 'mcq' && <McqView payload={payload} />}
      {item.kind === 'srq' && <SrqView payload={payload} />}

      {status === 'rejected' && note && !rejecting && (
        <p className="text-red-700 dark:text-red-400">Note: {note}</p>
      )}

      {rejecting ? (
        <div className="space-y-2">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What is wrong? e.g. option C is also correct; wrong unit in the answer"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              disabled={saving}
              onClick={() => save('rejected', note)}
            >
              Reject
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setRejecting(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={saving || status === 'approved'}
            onClick={() => save('approved')}
          >
            {saving ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <CheckIcon className="size-4" />
            )}
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={saving}
            onClick={() => setRejecting(true)}
          >
            <XIcon className="size-4" />
            Reject
          </Button>
        </div>
      )}
    </div>
  )
}

const ReviewList = ({
  gradeSubjectId,
  domainCode,
  kind,
  reviewStatus,
}: {
  gradeSubjectId: string
  domainCode?: string
  kind?: string
  reviewStatus?: string
}) => {
  const key = JSON.stringify({ gradeSubjectId, domainCode, kind, reviewStatus })
  const itemsResult = useAtomValue(reviewItemsAtom(key))

  return Result.builder(itemsResult)
    .onInitialOrWaiting(() => (
      <div className="flex items-center gap-2 p-8 text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin" />
        Loading items…
      </div>
    ))
    .onFailure(() => (
      <p className="p-8 text-destructive">Failed to load items</p>
    ))
    .onSuccess((items) => {
      if (items.length === 0) {
        return (
          <p className="p-8 text-center text-muted-foreground">
            Nothing here. Try another filter.
          </p>
        )
      }
      const groups: Array<{
        code: string
        description: string
        items: Array<ContentItemDto>
      }> = []
      for (const item of items) {
        const last = groups.at(-1)
        if (last && last.code === item.slo_code) last.items.push(item)
        else
          groups.push({
            code: item.slo_code,
            description: item.slo_description,
            items: [item],
          })
      }
      return (
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.code} className="space-y-2">
              <div className="sticky top-0 z-[1] border-b bg-background/95 py-2 backdrop-blur">
                <span className="font-mono text-sm font-semibold">
                  SLO {group.code}
                </span>
                <p className="line-clamp-2 text-sm text-muted-foreground">
                  {group.description}
                </p>
              </div>
              {group.items.map((item) => (
                <ItemCard key={item.id} item={item} />
              ))}
            </section>
          ))}
        </div>
      )
    })
    .render()
}

const Summary = ({ gradeSubjectId }: { gradeSubjectId: string }) => {
  const result = useAtomValue(reviewSummaryAtom(gradeSubjectId))
  if (!Result.isSuccess(result)) return null
  const totals = { draft: 0, approved: 0, rejected: 0 } as Record<
    string,
    number
  >
  for (const row of result.value)
    totals[row.review_status] = (totals[row.review_status] ?? 0) + row.count
  return (
    <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
      <span>{totals.draft} to review</span>
      <span className="text-emerald-600">{totals.approved} approved</span>
      <span className="text-red-600">{totals.rejected} rejected</span>
    </div>
  )
}

const DomainSelect = ({
  gradeSubjectId,
  value,
  onChange,
}: {
  gradeSubjectId: string
  value: string
  onChange: (value: string) => void
}) => {
  const treeResult = useAtomValue(curriculumTreeAtom(gradeSubjectId))
  const domains = Result.isSuccess(treeResult) ? treeResult.value.domains : []
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full sm:w-[220px]">
        <SelectValue placeholder="Domain" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>All domains</SelectItem>
        {domains.map((domain) => (
          <SelectItem key={domain.code} value={domain.code}>
            {domain.code} · {domain.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export const ReviewPage = () => {
  const reviewerResult = useAtomValue(reviewerStateAtom)
  const gradeSubjectsResult = useAtomValue(gradeSubjectsAtom)
  const available = useMemo(
    () =>
      Result.isSuccess(gradeSubjectsResult)
        ? gradeSubjectsResult.value.filter((gs) => gs.status === 'available')
        : [],
    [gradeSubjectsResult],
  )
  const [gradeSubjectId, setGradeSubjectId] = useState<string | null>(null)
  const [domain, setDomain] = useState('B')
  const [kind, setKind] = useState(ALL)
  const [status, setStatus] = useState('draft')
  const selected = gradeSubjectId ?? available.at(0)?.id ?? null

  const isReviewer =
    Result.isSuccess(reviewerResult) && reviewerResult.value.is_reviewer

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-2">
        <div className="flex flex-1 items-center gap-2 px-3">
          <SidebarTrigger />
          <Separator
            orientation="vertical"
            className="mr-2 data-[orientation=vertical]:h-4"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage className="font-medium">
                  Review content
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl space-y-4 p-4">
          {!isReviewer ? (
            <p className="p-8 text-center text-muted-foreground">
              {Result.isSuccess(reviewerResult)
                ? 'Only subject teachers who review content can open this page.'
                : 'Loading…'}
            </p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Check each item against the FBISE syllabus. Approve what is
                correct; reject anything wrong or unclear with a short note.
                Students only see approved and not-yet-reviewed items, never
                rejected ones.
              </p>
              <div className="flex flex-wrap gap-2">
                <Select
                  value={selected ?? undefined}
                  onValueChange={setGradeSubjectId}
                >
                  <SelectTrigger className="w-full sm:w-[200px]">
                    <SelectValue placeholder="Subject" />
                  </SelectTrigger>
                  <SelectContent>
                    {available.map((gs) => (
                      <SelectItem key={gs.id} value={gs.id}>
                        {gs.subject_name} {gradeName(gs.grade)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selected && (
                  <DomainSelect
                    gradeSubjectId={selected}
                    value={domain}
                    onChange={setDomain}
                  />
                )}
                <Select value={kind} onValueChange={setKind}>
                  <SelectTrigger className="w-full sm:w-[150px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {kinds.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger className="w-full sm:w-[150px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statuses.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selected && <Summary gradeSubjectId={selected} />}
              {selected && (
                <ReviewList
                  gradeSubjectId={selected}
                  domainCode={domain === ALL ? undefined : domain}
                  kind={kind === ALL ? undefined : kind}
                  reviewStatus={status === ALL ? undefined : status}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
