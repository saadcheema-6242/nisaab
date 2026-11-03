/**
 * Everything the practice records say, on one page.
 *
 * The dashboard already shows a summary per subject. This is the long view:
 * mastery against coverage, domain by domain, and the outcomes that are
 * actually losing marks - the things worth deciding what to revise from.
 *
 * It reads the progress endpoint that already exists and adds nothing to it.
 */

import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { BarChart3Icon } from 'lucide-react'
import type { SubjectProgressDto } from '@/integrations/api/client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { progressAtom } from '@/data-acess/progress'
import { SubjectIcon } from '@/lib/subjects'
import { BarRows, CoverageBar, Dial, percent } from './charts'
import type { Bar } from './charts'

const SubjectCard = ({ subject }: { subject: SubjectProgressDto }) => {
  const domains: Array<Bar> = (subject.domains ?? []).map((domain) => ({
    label: domain.name,
    value: domain.mastery ?? null,
    note:
      domain.practised_count === 0
        ? `0 of ${domain.examined_count}`
        : `${percent(domain.mastery)} · ${domain.practised_count}/${domain.examined_count}`,
  }))

  const weakest: Array<Bar> = (subject.weakest ?? []).slice(0, 6).map((slo) => ({
    label: `${slo.code} · ${slo.description}`,
    value: slo.mastery ?? null,
  }))

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <SubjectIcon code={subject.subject_code} className="size-4" />
          {subject.name}
          {subject.mastery !== null && subject.mastery !== undefined && (
            <Badge variant="secondary" className="ml-auto tabular-nums">
              {percent(subject.mastery)} mastery
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <CoverageBar
          practised={subject.practised_count}
          total={subject.examined_count}
        />

        {subject.predicted && (
          <Dial
            value={subject.predicted.percent}
            caption={subject.predicted.grade}
            sub={`${subject.predicted.descriptor} · estimated ${subject.predicted.percent}% · ${subject.predicted.confidence} confidence from ${percent(subject.predicted.coverage)} of the syllabus`}
          />
        )}

        <div className="space-y-2">
          <h3 className="text-sm font-medium">By chapter</h3>
          <BarRows bars={domains} empty="No chapters practised yet" />
        </div>

        {weakest.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Losing the most marks</h3>
            <BarRows bars={weakest} />
          </div>
        )}

        {(subject.suggested ?? []).length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Not practised yet</h3>
            <ul className="space-y-1 text-sm text-muted-foreground">
              {(subject.suggested ?? []).slice(0, 5).map((slo) => (
                <li key={slo.code} className="truncate">
                  <span className="font-mono text-xs">{slo.code}</span>{' '}
                  {slo.description}
                </li>
              ))}
            </ul>
          </div>
        )}

        <Link
          to="/dashboard/p/$projectId"
          params={{ projectId: subject.project_id }}
          className="inline-block text-sm font-medium text-primary hover:underline"
        >
          Open {subject.name}
        </Link>
      </CardContent>
    </Card>
  )
}

export const ProgressPage = () => {
  const progressResult = useAtomValue(progressAtom)

  if (!Result.isSuccess(progressResult)) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Loading your progress…
      </div>
    )
  }

  const subjects = progressResult.value.subjects.filter((s) => s.has_slos)

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <BarChart3Icon className="size-6" />
          Progress
        </h1>
        <p className="text-sm text-muted-foreground">
          Worked out from the questions you have actually answered. An outcome
          you have never attempted is not counted as a weakness — it is just
          not counted.
        </p>
      </header>

      {subjects.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            There is nothing to show yet. Answer a quiz or some flashcards and
            your progress will appear here.
          </CardContent>
        </Card>
      ) : (
        subjects.map((subject) => (
          <SubjectCard key={subject.project_id} subject={subject} />
        ))
      )}
    </div>
  )
}

export default ProgressPage
