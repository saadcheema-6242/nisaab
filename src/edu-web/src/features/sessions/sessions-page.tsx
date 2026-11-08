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
import { PageHeader } from '@/components/ui/page-header'

const Empty = ({ children }: { children: React.ReactNode }) => (
  <Card>
    <CardContent className="text-muted-foreground py-10 text-center text-sm">
      {children}
    </CardContent>
  </Card>
)

/** The classes this account is down to teach. Renders nothing for a student. */
const TeachingSection = () => {
  const result = useAtomValue(teachingAtom)
  if (!Result.isSuccess(result)) return null

  const { sessions, teacher } = result.value
  if (sessions.length === 0) return null

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

export const SessionsPage = () => (
  <div className="mx-auto w-full max-w-3xl space-y-6 p-4 md:p-6">
    <PageHeader icon={CalendarDaysIcon} title="Weekly sessions">
      Live classes with a teacher. A session is for a subject, so everyone
      studying it joins the same one, whichever group they are in.
    </PageHeader>

    <TeachingSection />
    <StudentSection />
  </div>
)

export default SessionsPage
