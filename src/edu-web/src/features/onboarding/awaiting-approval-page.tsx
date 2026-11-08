/**
 * Where a teacher waits.
 *
 * Nothing is granted by saying you are a teacher, so there is nothing to
 * show here except what was asked for and what happens next. The page polls,
 * rather than asking the person to keep reloading, because the moment of
 * approval is the moment they want to be let in.
 *
 * The way out matters as much as the waiting. Somebody will tap "Teacher" by
 * mistake, and without a button to become a student they are stuck: not
 * approved so not a teacher, no subjects so not a student, waiting on an
 * administrator who does not know they are waiting.
 */

import { useEffect, useState } from 'react'
import {
  Result,
  useAtom,
  useAtomRefresh,
  useAtomValue,
} from '@effect-atom/atom-react'
import { useNavigate } from '@tanstack/react-router'
import { ClockIcon, GraduationCapIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { accountStateAtom, withdrawTeacherAtom } from '@/data-acess/teachers'
import { brand } from '@/lib/brand'

const SUBJECT_NAMES: Record<string, string> = {
  PHY: 'Physics',
  CHEM: 'Chemistry',
  BIO: 'Biology',
  MATH: 'Mathematics',
  CS: 'Computer Science',
}

export const AwaitingApprovalPage = () => {
  const navigate = useNavigate()
  const refreshAccount = useAtomRefresh(accountStateAtom)
  const state = useAtomValue(accountStateAtom)
  const [withdrawing, withdraw] = useAtom(withdrawTeacherAtom)
  const [asking, setAsking] = useState(false)

  // Ask again every fifteen seconds. An administrator approving someone who
  // is sitting on this page should not have to tell them to refresh.
  useEffect(() => {
    const timer = setInterval(refreshAccount, 15_000)
    return () => clearInterval(timer)
  }, [refreshAccount])

  const account = Result.isSuccess(state) ? state.value : null

  // Approved, or no longer a teacher: either way this page is done.
  useEffect(() => {
    if (account && account.send_to === null) {
      navigate({ to: '/dashboard', replace: true })
    }
  }, [account, navigate])

  const profile = account?.teacher?.profile

  return (
    <div className="bg-background min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 py-10">
        <div className="mb-6">
          <div className="text-primary text-sm font-semibold">{brand.name}</div>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <ClockIcon className="size-5" />
              Waiting for approval
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p>
              Thank you. Your teacher account has been sent to an
              administrator. You will be let in as soon as they approve it,
              and this page will move on by itself.
            </p>

            {profile && (
              <div className="bg-muted/50 space-y-1.5 rounded-md p-3">
                <p className="flex items-center gap-2 font-medium">
                  <GraduationCapIcon className="size-4" />
                  What you told us
                </p>
                <p className="text-muted-foreground">
                  {profile.subjects
                    .map((code) => SUBJECT_NAMES[code] ?? code)
                    .join(', ')}
                  {' · '}
                  {profile.grades.map((g) => `Class ${g}`).join(' and ')}
                </p>
                {profile.school && (
                  <p className="text-muted-foreground">{profile.school}</p>
                )}
              </div>
            )}

            <div className="border-t pt-4">
              {asking ? (
                <div className="space-y-3">
                  <p>
                    Become a student instead? Your teacher application will be
                    withdrawn and you will be asked for your class and group.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={withdrawing.waiting}
                      onClick={() => withdraw()}
                    >
                      Yes, I am a student
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setAsking(false)}
                    >
                      Keep waiting
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground">
                  Chose this by mistake?{' '}
                  <button
                    type="button"
                    className="text-primary font-medium hover:underline"
                    onClick={() => setAsking(true)}
                  >
                    Switch to a student account
                  </button>
                  .
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default AwaitingApprovalPage
