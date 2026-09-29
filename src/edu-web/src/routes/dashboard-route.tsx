import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Navigate, Outlet } from '@tanstack/react-router'
import { profileAtom } from '@/data-acess/profile'

export const DashboardRoute = () => {
  const profileResult = useAtomValue(profileAtom)

  // New students choose their class, group and language first
  if (Result.isSuccess(profileResult) && !profileResult.value.onboarded) {
    return <Navigate to="/onboarding" />
  }

  return <Outlet />
}
