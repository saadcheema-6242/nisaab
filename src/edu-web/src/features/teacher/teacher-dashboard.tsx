/**
 * What an approved teacher sees at /dashboard.
 *
 * Until now there was no such page. The dashboard index rendered the
 * student's "My FSc" for everybody, so an approved teacher - who has no
 * StudentProfile and therefore no subjects - landed on an empty page
 * offering them "Set up my subjects": a button that would have walked them
 * into picking a class and group they have no business having.
 *
 * A teacher's question is not "what am I studying" but "when am I next in
 * front of a class, and what is the link". So that is the page: the next
 * class first and large, everything else under it.
 *
 * An administrator does not come here. They are deliberately both, and the
 * student dashboard is the more useful of the two for them, so the index
 * route keeps sending them there.
 */

import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import {
  CalendarDaysIcon,
  ExternalLinkIcon,
  GraduationCapIcon,
  MessageSquareIcon,
} from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import type { TeacherSession } from '@/data-acess/sessions'
import { SessionCard } from '@/features/sessions/session-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { LoadingLine } from '@/components/ui/loading-line'
import { Skeleton } from '@/components/ui/skeleton'
import { teachingAtom } from '@/data-acess/sessions'
import { accountStateAtom } from '@/data-acess/teachers'
import { brand } from '@/lib/brand'

/** The next class, given the room it deserves. */
const NextClass = ({ session }: { session: TeacherSession }) => {
  const live = session.state === 'open'
  return (
    <Card className="border-primary/25 bg-accent/40">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={live ? 'default' : 'soft'}>
            {live ? 'Live now' : 'Your next class'}
          </Badge>
          <span className="text-muted-foreground text-sm">{session.when}</span>
        </div>
        <CardTitle className="mt-1 text-2xl">{session.title}</CardTitle>
        <CardDescription>
          {session.subject_name} &middot; Year {session.grade}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* A teacher is given the link the whole time, not only inside the
            join window: they have to be in the room before the students
            are. The server decides that, in ClassSessionService.for_teacher;
            this only displays what it sent. */}
        {session.join_url ? (
          <Button asChild size="lg">
            <a href={session.join_url} target="_blank" rel="noreferrer">
              <ExternalLinkIcon />
              {live ? 'Join now' : 'Open the meeting link'}
            </a>
          </Button>
        ) : (
          <p className="text-muted-foreground text-sm">
            No meeting link on this one yet. Ask the administrator who scheduled
            it.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

const Shortcut = ({
  to,
  icon: Icon,
  title,
  blurb,
}: {
  to: string
  icon: React.ComponentType<{ className?: string }>
  title: string
  blurb: string
}) => (
  <Link to={to} className="group rounded-xl outline-none">
    <Card
      interactive
      className="group-focus-visible:ring-ring/45 h-full gap-3 group-focus-visible:ring-[3px]"
    >
      <CardHeader className="flex flex-row items-start gap-3">
        <div className="bg-accent text-accent-foreground grid size-10 shrink-0 place-items-center rounded-lg">
          <Icon className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{blurb}</CardDescription>
        </div>
      </CardHeader>
    </Card>
  </Link>
)

export const TeacherDashboard = () => {
  const account = useAtomValue(accountStateAtom)
  const result = useAtomValue(teachingAtom)
  const still = useReducedMotion()

  const teacher = Result.isSuccess(account) ? account.value.teacher : null
  const name = teacher?.name || 'Teacher'
  const subjects = teacher?.profile?.subjects ?? []

  return (
    <div className="bg-background min-h-screen p-4 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-8">
        <motion.header
          initial={still ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <h1 className="text-4xl font-semibold">Good to see you, {name}</h1>
          <div className="text-muted-foreground mt-3 flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="soft">
              <GraduationCapIcon className="size-3" /> Approved teacher
            </Badge>
            {teacher?.headline && <span>{teacher.headline}</span>}
            {subjects.length > 0 && <span>Teaching {subjects.join(', ')}</span>}
          </div>
        </motion.header>

        {Result.builder(result)
          .onInitialOrWaiting(() => (
            <div className="space-y-4">
              <Skeleton className="h-44 w-full rounded-xl" />
              <LoadingLine>Loading your classes</LoadingLine>
            </div>
          ))
          .onFailure(() => (
            <Card className="border-destructive/25 bg-destructive/[0.04]">
              <CardHeader>
                <CardTitle>We could not load your classes</CardTitle>
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
          .onSuccess((board) => {
            const next = board.next_session
            const rest = board.sessions.filter((s) => s.id !== next?.id)
            return (
              <>
                {next ? (
                  <NextClass session={next} />
                ) : (
                  // Said plainly, and said as the administrator's job rather
                  // than the teacher's. A teacher who sees an empty page with
                  // no explanation assumes the app is broken; the truthful
                  // answer is that nobody has timetabled them yet.
                  <Card className="border-dashed">
                    <CardHeader>
                      <CardTitle>No classes timetabled yet</CardTitle>
                      <CardDescription>
                        An administrator arranges the weekly sessions and
                        chooses who takes each one. When you are put in front of
                        a class it appears here with the meeting link, and every
                        student studying that subject sees it on their own
                        timetable.
                      </CardDescription>
                    </CardHeader>
                  </Card>
                )}

                {rest.length > 0 && (
                  <section className="space-y-3">
                    <h2 className="text-xl font-semibold tracking-[-0.01em]">
                      The rest of your week
                    </h2>
                    <div className="space-y-3">
                      {rest.map((one) => (
                        <SessionCard
                          key={one.id}
                          session={{ ...one, teacher: null }}
                          groups={one.groups}
                        />
                      ))}
                    </div>
                  </section>
                )}
              </>
            )
          })
          .render()}

        <section className="space-y-3">
          <h2 className="text-xl font-semibold tracking-[-0.01em]">
            Elsewhere
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Shortcut
              to="/dashboard/sessions"
              icon={CalendarDaysIcon}
              title="Weekly sessions"
              blurb="Every class on the timetable, yours and the rest."
            />
            <Shortcut
              to="/dashboard/community"
              icon={MessageSquareIcon}
              title="Class rooms"
              blurb="What students in your subjects are asking each other."
            />
          </div>
        </section>

        <p className="text-muted-foreground pt-4 text-center text-xs">
          {brand.notice}
        </p>
      </div>
    </div>
  )
}

export default TeacherDashboard
