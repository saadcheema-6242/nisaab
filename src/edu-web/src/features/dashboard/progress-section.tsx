import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { ChevronRightIcon } from 'lucide-react'
import type {
  ProgressSloDto,
  SubjectProgressDto,
} from '@/integrations/api/client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { progressAtom } from '@/data-acess/progress'
import { masteryLevel, masteryStyles } from '@/features/syllabus/slo-labels'
import { SubjectIcon } from '@/lib/subjects'
import { cn } from '@/lib/utils'

const percent = (value?: number | null) => `${Math.round((value ?? 0) * 100)}%`

const SloLink = ({
  projectId,
  slo,
}: {
  projectId: string
  slo: ProgressSloDto
}) => {
  const level = masteryLevel(slo.mastery)
  return (
    <li>
      <Link
        to="/dashboard/p/$projectId"
        params={{ projectId }}
        search={{ slo: slo.code }}
        className="flex items-start gap-2 rounded-lg p-2 text-sm hover:bg-accent/60"
      >
        <span
          className={cn(
            'mt-1.5 size-2 shrink-0 rounded-full',
            masteryStyles[level].dot,
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">
              {slo.code}
            </span>
            {slo.mastery != null && (
              <span className="text-xs font-medium">
                {percent(slo.mastery)}
              </span>
            )}
          </div>
          <p className="line-clamp-1">{slo.description}</p>
        </div>
        <span className="shrink-0 self-center text-xs font-medium text-primary">
          Practise
        </span>
      </Link>
    </li>
  )
}

const SubjectProgress = ({ subject }: { subject: SubjectProgressDto }) => {
  const predicted = subject.predicted
  const weakest = subject.weakest ?? []
  const suggested = subject.suggested ?? []
  const domains = subject.domains ?? []

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-3">
        <SubjectIcon code={subject.subject_code} />
        <CardTitle className="flex-1 text-lg">{subject.name}</CardTitle>
        <Link
          to="/dashboard/p/$projectId"
          params={{ projectId: subject.project_id }}
          className="flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          Syllabus map
          <ChevronRightIcon className="size-4" />
        </Link>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            Predicted grade
            <Badge variant="outline" className="text-[10px]">
              Estimate
            </Badge>
          </div>
          {predicted ? (
            <>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">{predicted.grade}</span>
                <span className="text-muted-foreground">
                  ≈ {predicted.percent}% · {predicted.descriptor}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                IBCC scale. Based on the {subject.practised_count} of{' '}
                {subject.examined_count} examined SLOs you have practised (
                {percent(predicted.coverage)} of teaching time)
                {predicted.confidence === 'low'
                  ? '. Practise more SLOs for a firmer estimate.'
                  : '.'}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Practise a few SLOs to see your predicted grade.
            </p>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">Mastery by domain</div>
          <ul className="space-y-1.5">
            {domains.map((domain) => {
              const level = masteryLevel(domain.mastery)
              return (
                <li key={domain.code} className="text-xs">
                  <div className="flex justify-between gap-2">
                    <span className="truncate">
                      {domain.code} · {domain.name}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {domain.mastery != null
                        ? `${percent(domain.mastery)} · `
                        : ''}
                      {domain.practised_count}/{domain.examined_count} SLOs
                    </span>
                  </div>
                  <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn('h-full', masteryStyles[level].bar)}
                      style={{ width: percent(domain.mastery) }}
                    />
                  </div>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="space-y-1">
          {weakest.length > 0 ? (
            <>
              <div className="text-sm font-medium">Needs work</div>
              <ul>
                {weakest.map((slo) => (
                  <SloLink
                    key={slo.code}
                    projectId={subject.project_id}
                    slo={slo}
                  />
                ))}
              </ul>
            </>
          ) : null}
          {suggested.length > 0 && weakest.length < 3 ? (
            <>
              <div className="text-sm font-medium">Start with</div>
              <ul>
                {suggested.map((slo) => (
                  <SloLink
                    key={slo.code}
                    projectId={subject.project_id}
                    slo={slo}
                  />
                ))}
              </ul>
            </>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export const ProgressSection = () => {
  const progressResult = useAtomValue(progressAtom)

  if (!Result.isSuccess(progressResult)) return null
  const subjects = progressResult.value.subjects.filter((s) => s.has_slos)
  if (subjects.length === 0) return null

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">My progress</h2>
      {subjects.map((subject) => (
        <SubjectProgress key={subject.project_id} subject={subject} />
      ))}
    </section>
  )
}
