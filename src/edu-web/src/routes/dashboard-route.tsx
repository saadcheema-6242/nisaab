import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Navigate, Outlet } from '@tanstack/react-router'
import { accountStateAtom } from '@/data-acess/teachers'

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

  if (Result.isSuccess(state) && state.value.send_to) {
    return <Navigate to={state.value.send_to} />
  }

  return <Outlet />
}
