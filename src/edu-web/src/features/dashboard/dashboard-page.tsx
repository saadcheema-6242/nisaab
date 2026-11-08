import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { ChevronRightIcon, FolderIcon, PlusIcon } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
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
import { Skeleton } from '@/components/ui/skeleton'
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
    className="group rounded-xl outline-none"
  >
    {/* `interactive` is what gives the lift and the focus ring; the card
        primitive owns both, so every grid of these behaves the same. */}
    <Card
      interactive
      className="h-full gap-4 group-focus-visible:ring-ring/45 group-focus-visible:ring-[3px]"
    >
      <CardHeader className="flex flex-row items-center gap-3">
        <SubjectIcon code={project.subject_code} className="size-11" />
        <div className="min-w-0 flex-1">
          <CardTitle className="text-lg">{project.name}</CardTitle>
          <CardDescription className="truncate">
            {project.description}
          </CardDescription>
        </div>
        {/* Slides towards the edge it points at, which is a cheaper way of
            saying "this goes somewhere" than any amount of copy. */}
        <ChevronRightIcon className="text-muted-foreground size-4 shrink-0 transition-transform duration-200 ease-out group-hover:translate-x-0.5 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0" />
      </CardHeader>
      <CardContent>
        {gradeSubject?.status === 'available' ? (
          <Badge variant="soft">
            Syllabus map · {gradeSubject.slo_count} SLOs
          </Badge>
        ) : (
          <Badge variant="outline">Syllabus map coming soon</Badge>
        )}
      </CardContent>
    </Card>
  </Link>
)

/**
 * What the grid looks like before the subjects arrive.
 *
 * Three cards' worth of grey blocks rather than the words "Loading your
 * subjects...". The point is that the page does not change shape when the
 * data lands: a line of centred text followed by a three-column grid is
 * the layout jumping, and on a first impression that reads as the app
 * stumbling even though it is working perfectly.
 */
const SubjectsLoading = () => (
  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
    {[0, 1, 2].map((i) => (
      <Card key={i} className="h-full gap-4">
        <CardHeader className="flex flex-row items-center gap-3">
          <Skeleton className="size-11 rounded-lg" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-5/6" />
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-5 w-32 rounded-md" />
        </CardContent>
      </Card>
    ))}
  </div>
)

/** A section title and its one-line explanation, set the same way everywhere. */
const SectionHead = ({
  title,
  blurb,
  action,
}: {
  title: string
  blurb?: string
  action?: React.ReactNode
}) => (
  <div className="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h2 className="text-xl font-semibold tracking-[-0.01em]">{title}</h2>
      {blurb && <p className="text-muted-foreground mt-1 text-sm">{blurb}</p>}
    </div>
    {action}
  </div>
)

export const DashboardPage = () => {
  const projectsResult = useAtomValue(projectsAtom)
  const profileResult = useAtomValue(profileAtom)
  const gradeSubjectsResult = useAtomValue(gradeSubjectsAtom)
  const openCreateProjectDialog = useCreateProjectDialog((state) => state.open)
  const still = useReducedMotion()

  const profile = Result.isSuccess(profileResult)
    ? profileResult.value.profile
    : null
  const gradeSubjects = Result.isSuccess(gradeSubjectsResult)
    ? gradeSubjectsResult.value
    : []

  return (
    <div className="bg-background min-h-screen p-4 sm:p-8">
      <div className="mx-auto max-w-6xl space-y-10">
        <motion.header
          initial={still ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <h1 className="text-4xl font-semibold">My FSc</h1>
          {profile && (
            // The three facts about this student's course, as chips rather
            // than a run-on sentence with a link buried in it. The old line
            // put "Change" at the end of a paragraph, where it read as part
            // of the sentence instead of as the control it is.
            <div className="text-muted-foreground mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm">
              <Badge variant="soft">{gradeName(profile.grade)}</Badge>
              <Badge variant="soft">{groupName(profile.group_code)}</Badge>
              <span>
                Explained in {languageName(profile.explanation_language)}
              </span>
              <Link
                to="/dashboard/settings"
                className="text-primary font-medium underline-offset-4 hover:underline"
              >
                Change
              </Link>
            </div>
          )}
        </motion.header>

        {Result.builder(projectsResult)
          .onInitialOrWaiting(() => (
            <section className="space-y-3">
              <SectionHead title="Subjects" />
              <SubjectsLoading />
            </section>
          ))
          .onFailure(() => (
            <Card className="border-destructive/25 bg-destructive/[0.04]">
              <CardHeader>
                <CardTitle>We could not load your subjects</CardTitle>
                <CardDescription>
                  The connection may have dropped. Reloading usually fixes it.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  onClick={() => window.location.reload()}
                >
                  Try again
                </Button>
              </CardContent>
            </Card>
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
                  <SectionHead title="Subjects" />
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
                      {subjects.map((project, i) => (
                        // Staggered by 40ms, which at five or six subjects
                        // reads as the grid settling into place rather than
                        // as six separate animations. Capped so a long list
                        // never leaves the last card waiting.
                        <motion.div
                          key={project.id}
                          initial={still ? false : { opacity: 0, y: 12 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{
                            duration: 0.35,
                            delay: Math.min(i * 0.04, 0.28),
                            ease: [0.22, 1, 0.36, 1],
                          }}
                        >
                          <SubjectCard
                            project={project}
                            gradeSubject={gradeSubjects.find(
                              (gs) => gs.id === project.grade_subject_id,
                            )}
                          />
                        </motion.div>
                      ))}
                    </div>
                  )}
                </section>

                <ProgressSection />

                <section className="space-y-3">
                  <SectionHead
                    title="My projects"
                    blurb="Your own notes and documents, outside the syllabus subjects"
                    action={
                      <Button
                        variant="outline"
                        onClick={() => openCreateProjectDialog()}
                      >
                        <PlusIcon />
                        New project
                      </Button>
                    }
                  />
                  {custom.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {custom.map((project) => (
                        <Link
                          key={project.id}
                          to="/dashboard/p/$projectId"
                          params={{ projectId: project.id }}
                          className="group rounded-xl outline-none"
                        >
                          <Card
                            interactive
                            className="h-full group-focus-visible:ring-ring/45 group-focus-visible:ring-[3px]"
                          >
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <FolderIcon className="size-5 shrink-0" />
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
                  ) : (
                    // Previously this section rendered a heading, a button
                    // and then nothing, so the page ended on a void. An
                    // empty state is the difference between "you have none
                    // yet" and "something failed to load".
                    <div className="border-border/70 bg-muted/30 flex flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center">
                      <div className="bg-accent text-accent-foreground grid size-10 place-items-center rounded-full">
                        <FolderIcon className="size-5" />
                      </div>
                      <p className="text-muted-foreground max-w-sm text-sm leading-relaxed">
                        Nothing here yet. A project is a place for your own
                        notes, past papers or anything outside the nine FBISE
                        subjects.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openCreateProjectDialog()}
                      >
                        <PlusIcon />
                        Make your first project
                      </Button>
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
