import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { ChevronRightIcon, FolderIcon, PlusIcon } from 'lucide-react'
import { ProgressSection } from './progress-section'
import type { GradeSubjectDto, ProjectDto } from '@/integrations/api/client'
import { gradeSubjectsAtom } from '@/data-acess/curriculum'
import { profileAtom } from '@/data-acess/profile'
import { projectsAtom } from '@/data-acess/project'
import { useCreateProjectDialog } from '@/features/project/components/upsert-project-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { brand } from '@/lib/brand'
import { languageName } from '@/lib/languages'
import { SubjectIcon, gradeName, groupName } from '@/lib/subjects'

const SubjectCard = ({
  project,
  gradeSubject,
}: {
  project: ProjectDto
  gradeSubject?: GradeSubjectDto
}) => (
  <Link
    to="/dashboard/p/$projectId"
    params={{ projectId: project.id }}
    className="group"
  >
    <Card className="h-full transition-shadow group-hover:shadow-md">
      <CardHeader className="flex flex-row items-center gap-3">
        <SubjectIcon code={project.subject_code} className="size-11" />
        <div className="min-w-0 flex-1">
          <CardTitle className="text-lg">{project.name}</CardTitle>
          <CardDescription className="truncate">
            {project.description}
          </CardDescription>
        </div>
        <ChevronRightIcon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {gradeSubject?.status === 'available' ? (
          <Badge variant="secondary">
            Syllabus map · {gradeSubject.slo_count} SLOs
          </Badge>
        ) : (
          <Badge variant="outline">Syllabus map coming soon</Badge>
        )}
      </CardContent>
    </Card>
  </Link>
)

export const DashboardPage = () => {
  const projectsResult = useAtomValue(projectsAtom)
  const profileResult = useAtomValue(profileAtom)
  const gradeSubjectsResult = useAtomValue(gradeSubjectsAtom)
  const openCreateProjectDialog = useCreateProjectDialog((state) => state.open)

  const profile = Result.isSuccess(profileResult)
    ? profileResult.value.profile
    : null
  const gradeSubjects = Result.isSuccess(gradeSubjectsResult)
    ? gradeSubjectsResult.value
    : []

  return (
    <div className="min-h-screen bg-background p-4 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">My FSc</h1>
            {profile && (
              <p className="mt-2 text-muted-foreground">
                {gradeName(profile.grade)} · {groupName(profile.group_code)} ·
                Tutor explains in {languageName(profile.explanation_language)}{' '}
                <Link
                  to="/dashboard/settings"
                  className="underline underline-offset-2"
                >
                  Change
                </Link>
              </p>
            )}
          </div>
        </div>

        {Result.builder(projectsResult)
          .onInitialOrWaiting(() => (
            <div className="py-12 text-center">
              <p className="text-muted-foreground">Loading your subjects...</p>
            </div>
          ))
          .onFailure(() => (
            <div className="py-12 text-center">
              <p className="text-destructive">Failed to load your subjects</p>
            </div>
          ))
          .onSuccess((projects) => {
            const subjects = projects.filter(
              (p) => p.kind === 'subject_workspace',
            )
            const custom = projects.filter(
              (p) => p.kind !== 'subject_workspace',
            )

            return (
              <>
                <section className="space-y-3">
                  <h2 className="text-lg font-semibold">Subjects</h2>
                  {subjects.length === 0 ? (
                    <Card>
                      <CardHeader>
                        <CardTitle>No subjects yet</CardTitle>
                        <CardDescription>
                          Choose your class and group to get your FBISE
                          subjects.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Button asChild>
                          <Link to="/onboarding">Set up my subjects</Link>
                        </Button>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {subjects.map((project) => (
                        <SubjectCard
                          key={project.id}
                          project={project}
                          gradeSubject={gradeSubjects.find(
                            (gs) => gs.id === project.grade_subject_id,
                          )}
                        />
                      ))}
                    </div>
                  )}
                </section>

                <ProgressSection />

                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold">My projects</h2>
                      <p className="text-sm text-muted-foreground">
                        Your own notes and documents, outside the syllabus
                        subjects
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => openCreateProjectDialog()}
                    >
                      <PlusIcon className="mr-2 h-4 w-4" />
                      New project
                    </Button>
                  </div>
                  {custom.length > 0 && (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {custom.map((project) => (
                        <Link
                          key={project.id}
                          to="/dashboard/p/$projectId"
                          params={{ projectId: project.id }}
                        >
                          <Card className="h-full transition-shadow hover:shadow-md">
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <FolderIcon className="h-5 w-5" />
                                {project.name}
                              </CardTitle>
                              {project.description && (
                                <CardDescription>
                                  {project.description}
                                </CardDescription>
                              )}
                            </CardHeader>
                          </Card>
                        </Link>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )
          })
          .render()}

        <p className="pt-4 text-center text-xs text-muted-foreground">
          {brand.notice}
        </p>
      </div>
    </div>
  )
}
