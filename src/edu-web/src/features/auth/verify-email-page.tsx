import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useState } from 'react'
import { useAtom, useAtomValue } from '@effect-atom/atom-react'
import { Button } from '@/components/ui/button'
import { authAtom, signOutAtom } from '@/data-acess/auth'
import { reloadUser, resendVerification } from '@/lib/auth-client'

/**
 * The step between signing up and using NISAAB.
 *
 * Without it a new student landed on the dashboard, every request came back
 * 403, and the page said "Failed to load your subjects" - which reads as a
 * broken app, not as "we are waiting for you to confirm your address". They
 * were never told an email had been sent, so they had no reason to look for
 * it.
 *
 * Firebase sends a link, not a code. There is no code to type: the student
 * opens the inbox, clicks, and comes back. So this page polls instead of
 * asking for input, and the student usually finds it has already moved on by
 * the time they switch back to the tab.
 */
export const VerifyEmailPage = () => {
  const navigate = useNavigate()
  const auth = useAtomValue(authAtom)
  const [, signOut] = useAtom(signOutAtom)

  const [checking, setChecking] = useState(false)
  const [sending, setSending] = useState(false)
  const [sentAt, setSentAt] = useState<number | null>(null)
  const [notYet, setNotYet] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const email = auth.user?.email ?? ''

  // Someone who arrives here already confirmed (a Google account, or a second
  // tab) should not be held up by a page about confirming.
  useEffect(() => {
    if (auth.user?.emailVerified) navigate({ to: '/dashboard' })
  }, [auth.user?.emailVerified, navigate])

  const check = useCallback(
    async (manual: boolean) => {
      if (manual) {
        setChecking(true)
        setNotYet(false)
      }
      try {
        if (await reloadUser()) {
          navigate({ to: '/dashboard' })
          return true
        }
        if (manual) setNotYet(true)
      } catch {
        // A failed check is not worth an error message on a timer. The next
        // poll tries again, and the button says so if the student presses it.
        if (manual) setError('Could not check just now. Try again in a moment.')
      } finally {
        if (manual) setChecking(false)
      }
      return false
    },
    [navigate],
  )

  // Clicking the link happens in another tab, so nothing tells this one. A
  // poll every four seconds is what makes the page move on by itself; the
  // button is there for anyone who does not wait.
  useEffect(() => {
    if (!auth.user) return
    const timer = setInterval(() => void check(false), 4000)
    return () => clearInterval(timer)
  }, [auth.user, check])

  const resend = async () => {
    setSending(true)
    setError(null)
    setNotYet(false)
    try {
      await resendVerification()
      setSentAt(Date.now())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send the email.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center px-4 py-10">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">Confirm your email</h1>
          <p className="text-muted-foreground text-sm">
            We sent a link to{' '}
            <span className="text-foreground font-medium break-all">
              {email || 'your email address'}
            </span>
            . Open it and this page will carry on by itself.
          </p>
        </div>

        <div className="bg-muted/40 text-muted-foreground rounded-lg border p-4 text-left text-sm">
          <p className="mb-2 font-medium">Not arrived?</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>It can take a minute.</li>
            <li>Check the spam or promotions folder.</li>
            <li>
              If the address above is wrong, sign out and sign up again, or use
              Continue with Google.
            </li>
          </ul>
        </div>

        {notYet && (
          <p className="text-sm text-amber-600 dark:text-amber-500">
            Not confirmed yet. Open the link in the email, then press this
            again.
          </p>
        )}
        {sentAt !== null && !error && (
          <p className="text-sm text-emerald-600 dark:text-emerald-500">
            Sent again. Have another look in your inbox.
          </p>
        )}
        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="space-y-2">
          <Button
            className="w-full"
            onClick={() => void check(true)}
            disabled={checking}
          >
            {checking ? 'Checking...' : "I've confirmed it"}
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => void resend()}
            disabled={sending}
          >
            {sending ? 'Sending...' : 'Send the email again'}
          </Button>
        </div>

        <button
          type="button"
          className="text-muted-foreground hover:text-foreground text-sm underline underline-offset-4"
          onClick={() => {
            signOut()
            navigate({ to: '/sign-in' })
          }}
        >
          Use a different account
        </button>
      </div>
    </div>
  )
}
