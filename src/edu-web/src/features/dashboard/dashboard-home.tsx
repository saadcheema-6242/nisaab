/**
 * Which dashboard this account gets.
 *
 * The index route used to render the student page unconditionally. An
 * approved teacher has no StudentProfile, so they arrived at a page with
 * no subjects on it and a button offering to set some up - which would
 * have put a teacher through student onboarding.
 *
 * The split is here rather than in the route table because the answer
 * depends on a server response, and the route table has no way to wait for
 * one. Nothing is rendered until the answer is in: guessing student and
 * correcting would show a teacher a flash of the page this exists to keep
 * them off.
 *
 * An administrator is deliberately both and keeps the student page, which
 * is the more useful of the two for them; their teaching, if any, is on
 * the sessions page.
 */

import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Suspense, lazy } from 'react'
import { DashboardPage } from './dashboard-page'
import { LoadingLine } from '@/components/ui/loading-line'
import { accountStateAtom } from '@/data-acess/teachers'

// Lazily, so a student never downloads the teacher page and a teacher
// never downloads the subject grid.
const TeacherDashboard = lazy(() =>
  import('@/features/teacher/teacher-dashboard').then((m) => ({
    default: m.TeacherDashboard,
  })),
)

export const DashboardHome = () => {
  const account = useAtomValue(accountStateAtom)

  // The guard above this route has already held the page until this atom
  // resolved, so in practice it is ready. Checked anyway: rendering the
  // student page while unsure is the exact bug being fixed.
  if (!Result.isSuccess(account)) {
    return <LoadingLine>Loading your dashboard</LoadingLine>
  }

  const { role, is_admin, teacher_approved } = account.value
  if (role === 'teacher' && teacher_approved && !is_admin) {
    return (
      <Suspense fallback={<LoadingLine>Loading your classes</LoadingLine>}>
        <TeacherDashboard />
      </Suspense>
    )
  }

  return <DashboardPage />
}
