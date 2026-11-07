import { Atom } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import type { AuthUser } from '@/lib/auth-client'
import { ApiClientService } from '@/integrations/api/http'
import {
  getCurrentUser,
  onAuthChange,
  signIn,
  signInWithGoogle,
  signOut,
  signUp,
} from '@/lib/auth-client'

export const currentUserAtom = Atom.make(
  Effect.gen(function* () {
    const { apiClient } = yield* ApiClientService
    const resp = yield* apiClient.getCurrentUserInfoApiV1AuthMeGet()

    const name = resp.name?.trim() ?? resp.email?.split('@')[0] ?? 'User'

    const initials = name
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)

    return {
      ...resp,
      name,
      initials,
    }
  }).pipe(Effect.provide(ApiClientService.Default)),
).pipe(Atom.keepAlive)

type AuthSession = { user: AuthUser }

const toState = (user: AuthUser | null) => ({
  session: user ? { user } : null,
  user,
})

export const authAtom: Atom.Atom<{
  session: AuthSession | null
  user: AuthUser | null
}> = Atom.make((get) => {
  getCurrentUser().then((user) => get.setSelf(toState(user)))

  const unsubscribe = onAuthChange((user) => get.setSelf(toState(user)))
  get.addFinalizer(() => unsubscribe())

  return { session: null, user: null }
})

export const isAuthenticatedAtom = Atom.make((get) => {
  const auth = get(authAtom)
  return !!auth.session && !!auth.user
})

type SignInPayload = {
  readonly type: 'password'
  readonly email: string
  readonly password: string
}

export const signInAtom = Atom.fn(
  Effect.fn(function* (payload: SignInPayload) {
    yield* Effect.promise(() => signIn(payload.email, payload.password))
  }),
)

export const signUpAtom = Atom.fn(
  Effect.fn(function* (payload: { email: string; password: string }) {
    yield* Effect.promise(() => signUp(payload.email, payload.password))
  }),
)

/**
 * Sign in with Google.
 *
 * Google has already confirmed the address, so an account arriving this way
 * is verified from the start and never meets the confirmation step. It is the
 * quickest route in for a student who mistyped their email and cannot receive
 * the link.
 */
export const signInWithGoogleAtom = Atom.fn(
  Effect.fn(function* () {
    yield* Effect.promise(() => signInWithGoogle())
  }),
)

export const signOutAtom = Atom.fn(
  Effect.fn(function* () {
    yield* Effect.promise(() => signOut())
  }),
)
