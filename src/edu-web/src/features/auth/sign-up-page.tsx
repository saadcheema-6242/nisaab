import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { CheckIcon, MailIcon } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import {
  AuthError,
  AuthShell,
  GoogleMark,
  OrRule,
} from '@/components/auth/auth-shell'

export const SignUpPage = () => {
  const { signUp, signInWithGoogle, isLoading, signUpError, isAuthenticated } =
    useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: '/sign-up' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [hasSubmitted, setHasSubmitted] = useState(false)

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !hasSubmitted) {
      const redirectUrl =
        search?.redirect || sessionStorage.getItem('auth.redirect')
      if (redirectUrl) {
        sessionStorage.removeItem('auth.redirect')
        const dashboardUrl = redirectUrl.startsWith('/dashboard')
          ? redirectUrl
          : `/dashboard${redirectUrl}`
        navigate({ to: dashboardUrl })
      } else {
        navigate({ to: '/dashboard' })
      }
    }
  }, [isAuthenticated, navigate, search?.redirect, hasSubmitted])

  // Update error when signUpError changes
  useEffect(() => {
    if (signUpError) {
      setError(
        signUpError instanceof Error
          ? signUpError.message
          : 'Sign up failed. Please try again.',
      )
      setHasSubmitted(false)
    }
  }, [signUpError])

  // Handle successful sign-up
  useEffect(() => {
    if (hasSubmitted && !isLoading && !signUpError) {
      if (isAuthenticated) {
        // The account exists but the address has not been confirmed, and the
        // API refuses it until it is. Sending them to the dashboard produced
        // a page where every panel failed with no explanation; requireAuth
        // would bounce them here anyway, and the bounce is visible. Go
        // straight to the step that tells them what is waiting in the inbox.
        navigate({ to: '/verify-email' })
      } else {
        setSuccess(true)
      }
    }
  }, [
    hasSubmitted,
    isLoading,
    signUpError,
    isAuthenticated,
    navigate,
    search?.redirect,
  ])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    setHasSubmitted(false)

    if (!email || !password || !confirmPassword) {
      setError('Please fill in all fields')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long')
      return
    }

    // Store the redirect URL before sign up
    if (search?.redirect) {
      sessionStorage.setItem('auth.redirect', search.redirect)
    }

    setHasSubmitted(true)
    signUp({ email, password })
  }

  // Said as soon as both fields have something in them, rather than held
  // back until submit. Learning the passwords differ after pressing the
  // button means retyping both; learning it while typing means fixing one
  // character.
  const mismatch =
    confirmPassword.length > 0 && password !== confirmPassword
      ? 'Those do not match yet.'
      : null
  const matched =
    confirmPassword.length > 0 &&
    password === confirmPassword &&
    password.length >= 6

  if (success) {
    return (
      <AuthShell
        title="Check your email"
        blurb="Your account is made. One more step to prove the address is yours."
        footer={
          <Link
            to="/sign-in"
            className="text-primary text-sm font-medium underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        }
      >
        <div className="space-y-4 text-center">
          <div className="bg-accent text-accent-foreground mx-auto grid size-12 place-items-center rounded-full">
            <MailIcon className="size-5" />
          </div>
          <p className="text-sm">
            We sent a confirmation link to{' '}
            <strong className="text-foreground font-medium">{email}</strong>
          </p>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Open it to verify your account and finish signing up. If it is not
            there in a minute, check the spam folder.
          </p>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title="Create an account"
      blurb="Free, and it takes a minute."
      footer={
        <>
          <p className="text-muted-foreground text-sm">
            Already have an account?{' '}
            <Link
              to="/sign-in"
              search={
                search?.redirect ? { redirect: search.redirect } : undefined
              }
              className="text-primary font-medium underline-offset-4 hover:underline"
            >
              Sign in
            </Link>
          </p>
          <p className="text-muted-foreground text-xs">
            By creating an account you agree to our{' '}
            <a
              href="/privacy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline-offset-4 hover:underline"
            >
              Privacy Policy
            </a>
          </p>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="you@example.com"
            autoComplete="email"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="At least 6 characters"
            autoComplete="new-password"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm password</Label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            placeholder="Type it again"
            autoComplete="new-password"
            disabled={isLoading}
            aria-invalid={mismatch !== null}
            aria-describedby="confirm-hint"
          />
          {/* The row is always present, so the form does not jump by a line
              the moment someone starts typing in it. */}
          <p id="confirm-hint" aria-live="polite" className="min-h-4 text-xs">
            {mismatch ? (
              <span className="text-destructive">{mismatch}</span>
            ) : matched ? (
              <span className="text-accent-foreground inline-flex items-center gap-1">
                <CheckIcon className="size-3" /> Passwords match
              </span>
            ) : null}
          </p>
        </div>

        {error && <AuthError>{error}</AuthError>}

        <Button
          type="submit"
          size="lg"
          className="w-full"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <Spinner /> Creating account
            </>
          ) : (
            'Create account'
          )}
        </Button>

        <OrRule />

        {/* Google has already confirmed the address, so this route never
            meets the email confirmation step. It is also the way back in
            for a student who mistyped their email on sign-up. */}
        <Button
          type="button"
          variant="outline"
          size="lg"
          className="w-full"
          disabled={isLoading}
          onClick={() => signInWithGoogle()}
        >
          <GoogleMark /> Continue with Google
        </Button>
      </form>
    </AuthShell>
  )
}
