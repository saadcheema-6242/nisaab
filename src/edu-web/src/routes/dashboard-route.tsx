import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Navigate, Outlet, useLocation } from '@tanstack/react-router'
import { accountStateAtom } from '@/data-acess/teachers'
import { surfaceFor, teacherMayOpen } from '@/lib/surface'

/**
 * Where an account is allowed to be.
 *
 * One question to the server, answered before anything renders: a student
 * who has not chosen their subjects goes to onboarding, a teacher waiting
 * for approval goes to the waiting page, everybody else carries on. The
 * server decides, in edu_core.roles.needs_onboarding, so the rule exists
 * once rather than being re-derived here from three separate facts.
 *
 * Nothing is rendered until the answer arrives. Guessing and correcting
 * would show a teacher awaiting approval a flash of the student dashboard,
 * which is the thing approval exists to prevent.
 */
export const DashboardRoute = () => {
  const state = useAtomValue(accountStateAtom)
  const { pathname } = useLocation()

  if (Result.isSuccess(state)) {
    if (state.value.send_to) {
      return <Navigate to={state.value.send_to} />
    }
    // A teacher typing /dashboard/community, or following an old link,
    // reaches a page that reads a StudentProfile they do not have. The
    // sidebar already does not offer it; this is what makes that true
    // rather than merely tidy. Sent to their own dashboard rather than
    // shown a refusal: there is nothing for them to do about it, and the
    // page they wanted does not exist for their kind of account.
    if (surfaceFor(state.value) === 'teacher' && !teacherMayOpen(pathname)) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <Outlet />
}
