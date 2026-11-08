import { useNavigate } from '@tanstack/react-router'
import { useCallback, useEffect, useState } from 'react'
import { useAtom, useAtomValue } from '@effect-atom/atom-react'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { AuthError, AuthShell } from '@/components/auth/auth-shell'
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
    <AuthShell
      title="Confirm your email"
      footer={
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
      }
    >
      <div className="space-y-5">
        <p className="text-muted-foreground text-center text-sm leading-relaxed">
          We sent a link to{' '}
          <span className="text-foreground font-medium break-all">
            {email || 'your email address'}
          </span>
          . Open it and this page will carry on by itself.
        </p>

        {/* A live region, so the poll finding nothing does not silently
            replace the one thing a screen reader was told. */}
        <div aria-live="polite" className="space-y-2 empty:hidden">
          {notYet && (
            <p className="rounded-lg border border-amber-500/25 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
              Not confirmed yet. Open the link in the email, then press this
              again.
            </p>
          )}
          {sentAt !== null && !error && (
            <p className="border-accent-foreground/20 bg-accent text-accent-foreground rounded-lg border p-3 text-sm">
              Sent again. Have another look in your inbox.
            </p>
          )}
          {error && <AuthError>{error}</AuthError>}
        </div>

        <div className="space-y-2">
          <Button
            size="lg"
            className="w-full"
            onClick={() => void check(true)}
            disabled={checking}
          >
            {checking ? (
              <>
                <Spinner /> Checking
              </>
            ) : (
              "I've confirmed it"
            )}
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="w-full"
            onClick={() => void resend()}
            disabled={sending}
          >
            {sending ? (
              <>
                <Spinner /> Sending
              </>
            ) : (
              'Send the email again'
            )}
          </Button>
        </div>

        <div className="bg-muted/40 border-border/70 text-muted-foreground rounded-lg border p-4 text-sm">
          <p className="text-foreground mb-2 font-medium">Not arrived?</p>
          <ul className="list-disc space-y-1 pl-5 leading-relaxed">
            <li>It can take a minute.</li>
            <li>Check the spam or promotions folder.</li>
            <li>
              If the address above is wrong, sign out and sign up again, or use
              Continue with Google.
            </li>
          </ul>
        </div>
      </div>
    </AuthShell>
  )
}
