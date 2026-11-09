import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useAtom, useAtomValue } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  AuthError,
  AuthShell,
  GoogleMark,
  OrRule,
} from '@/components/auth/auth-shell'
import { Spinner } from '@/components/ui/spinner'
import {
  isAuthenticatedAtom,
  signInAtom,
  signInWithGoogleAtom,
} from '@/data-acess/auth'

export const SignInPage = () => {
  const [signInResult, signIn] = useAtom(signInAtom)
  const [, signInWithGoogle] = useAtom(signInWithGoogleAtom)
  const isAuthenticated = useAtomValue(isAuthenticatedAtom)

  const isLoading = signInResult.waiting

  const navigate = useNavigate()
  const search = useSearch({ from: '/sign-in' })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // const [error, setError] = useState<string | null>(null)

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
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
  }, [isAuthenticated, navigate, search?.redirect])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !password) {
      // setError('Please enter both email and password')
      return
    }

    // Store the redirect URL before login
    if (search?.redirect) {
      sessionStorage.setItem('auth.redirect', search.redirect)
    }

    signIn({ type: 'password', email, password })
  }

  return (
    <AuthShell
      title="Welcome back"
      blurb="Sign in to pick up where you left off."
      footer={
        <>
          <p className="text-muted-foreground text-sm">
            Don&apos;t have an account?{' '}
            <Link
              to="/sign-up"
              search={
                search?.redirect ? { redirect: search.redirect } : undefined
              }
              className="text-primary font-medium underline-offset-4 hover:underline"
            >
              Sign up
            </Link>
          </p>
          <p className="text-muted-foreground text-xs">
            By signing in you agree to our{' '}
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
          <div className="flex items-baseline justify-between">
            <Label htmlFor="password">Password</Label>
          </div>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="Your password"
            autoComplete="current-password"
            disabled={isLoading}
          />
        </div>

        {signInResult._tag === 'Failure' && (
          <AuthError>
            {(() => {
              const thrown: unknown = Cause.squash(signInResult.cause)
              return thrown instanceof Error && thrown.message
                ? thrown.message
                : 'Sign in failed'
            })()}
          </AuthError>
        )}

        {/* The label changes rather than the button emptying out, so the
            width does not jump and the spinner has something to sit beside. */}
        <Button type="submit" size="lg" className="w-full" disabled={isLoading}>
          {isLoading ? (
            <>
              <Spinner /> Signing in
            </>
          ) : (
            'Sign in'
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
