/**
 * The student's timetable, and the teacher's, on one page.
 *
 * One page rather than two routes because an account is one or the other and
 * nobody should have to know which link to open. A teacher sees the classes
 * they are taking; everyone else sees the classes they can attend. The
 * teacher section simply has nothing in it for a student, so it is not shown.
 */

import { Result, useAtomValue } from '@effect-atom/atom-react'
import { CalendarDaysIcon, GraduationCapIcon } from 'lucide-react'
import { SessionCard } from './session-card'
import { Card, CardContent } from '@/components/ui/card'
import { mySessionsAtom, teachingAtom } from '@/data-acess/sessions'
import { accountStateAtom } from '@/data-acess/teachers'
import { surfaceFor } from '@/lib/surface'
import { PageHeader } from '@/components/ui/page-header'

const Empty = ({ children }: { children: React.ReactNode }) => (
  <Card>
    <CardContent className="text-muted-foreground py-10 text-center text-sm">
      {children}
    </CardContent>
  </Card>
)

/**
 * The classes this account is down to teach.
 *
 * `showEmpty` is the difference between a student and a teacher looking at
 * this page. For a student the section is noise and is left out entirely.
 * For a teacher an empty list is the answer to their question, and hiding
 * it - which is what this did - left a teacher with no classes staring at
 * a page that mentioned teaching nowhere, looking exactly like the app had
 * failed to load.
 */
const TeachingSection = ({ showEmpty = false }: { showEmpty?: boolean }) => {
  const result = useAtomValue(teachingAtom)
  if (!Result.isSuccess(result)) return null

  const { sessions, teacher } = result.value
  if (sessions.length === 0 && !showEmpty) return null

  if (sessions.length === 0) {
    return (
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <GraduationCapIcon className="size-5" />
          <h2 className="text-lg font-semibold">Your classes</h2>
        </div>
        <Empty>
          You are not down to take a class yet. An administrator arranges the
          weekly sessions and chooses who takes each one.
        </Empty>
      </section>
    )
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <GraduationCapIcon className="size-5" />
        <h2 className="text-lg font-semibold">Your classes</h2>
      </div>
      <p className="text-muted-foreground text-sm">
        {teacher.name}, you are taking {sessions.length}{' '}
        {sessions.length === 1 ? 'class' : 'classes'}. The join link is here the
        whole time so you can start early.
      </p>
      <div className="space-y-3">
        {sessions.map((one) => (
          <SessionCard
            key={one.id}
            session={{ ...one, teacher: null }}
            groups={one.groups}
          />
        ))}
      </div>
    </section>
  )
}

const StudentSection = () => {
  const result = useAtomValue(mySessionsAtom)

  if (Result.isFailure(result)) {
    return (
      <Empty>Your sessions could not be loaded. Try again in a moment.</Empty>
    )
  }
  if (!Result.isSuccess(result)) {
    return <p className="text-muted-foreground p-6 text-sm">Loading…</p>
  }

  const { sessions } = result.value
  if (sessions.length === 0) {
    return (
      <Empty>
        No sessions are scheduled yet. When a teacher is timetabled for one of
        your subjects, it will appear here.
      </Empty>
    )
  }

  return (
    <div className="space-y-3">
      {sessions.map((one) => (
        <SessionCard key={one.id} session={one} />
      ))}
    </div>
  )
}

/**
 * A teacher has no cohort, so the student timetable is not merely empty for
 * them, it is unanswerable: `for_student` reads a StudentProfile they do
 * not have and correctly returns nothing. Showing them "No sessions are
 * scheduled yet. When a teacher is timetabled for one of your subjects..."
 * told a teacher about subjects they do not study. They see their own
 * classes instead.
 *
 * An administrator sees both, as everywhere else: they are a student of
 * every cohort and a teacher.
 */
export const SessionsPage = () => {
  const account = useAtomValue(accountStateAtom)
  const surface = Result.isSuccess(account)
    ? surfaceFor(account.value)
    : 'student'
  // An administrator is both, so they get the teaching section as well as
  // the timetable; a teacher gets only their own classes.
  const teacherOnly = surface === 'teacher'
  const teaches = teacherOnly || surface === 'admin'

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
      <PageHeader icon={CalendarDaysIcon} title="Weekly sessions">
        Live classes with a teacher. A session is for a subject, so everyone
        studying it joins the same one, whichever group they are in.
      </PageHeader>

      <TeachingSection showEmpty={teaches} />
      {!teacherOnly && <StudentSection />}
    </div>
  )
}

export default SessionsPage
