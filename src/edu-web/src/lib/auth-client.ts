import { initializeApp } from 'firebase/app'
import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
} from 'firebase/auth'
import { FirebaseError } from 'firebase/app'
import { Effect } from 'effect'
import type { User } from 'firebase/auth'
import { env } from '@/env'

// Google Identity Platform (Firebase Authentication): email and password sign-in
const app = initializeApp({
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain:
    env.VITE_FIREBASE_AUTH_DOMAIN ?? `${env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
})

export const auth = getAuth(app)
export type AuthUser = User

const ERROR_MESSAGES: Record<string, string> = {
  'auth/invalid-credential': 'Wrong email or password.',
  'auth/invalid-email': 'Please enter a valid email address.',
  'auth/user-disabled': 'This account has been disabled.',
  'auth/email-already-in-use': 'An account with this email already exists. Please sign in.',
  'auth/weak-password': 'Password must be at least 6 characters.',
  'auth/too-many-requests': 'Too many attempts. Please wait a minute and try again.',
  'auth/network-request-failed': 'Network error. Check your connection and try again.',
}

/** Turn Firebase errors into messages students can act on. */
const friendly = (error: unknown): Error => {
  if (error instanceof FirebaseError) {
    return new Error(ERROR_MESSAGES[error.code] ?? 'Something went wrong. Please try again.')
  }
  return error instanceof Error ? error : new Error(String(error))
}

const withFriendlyErrors = async <T>(action: () => Promise<T>): Promise<T> => {
  try {
    return await action()
  } catch (error) {
    throw friendly(error)
  }
}

/** The signed-in user, once Firebase has restored any saved session. */
export const getCurrentUser = async (): Promise<User | null> => {
  await auth.authStateReady()
  return auth.currentUser
}

export const onAuthChange = (callback: (user: User | null) => void) =>
  onAuthStateChanged(auth, callback)

export const signIn = (email: string, password: string) =>
  withFriendlyErrors(() => signInWithEmailAndPassword(auth, email, password))

export const signUp = (email: string, password: string) =>
  withFriendlyErrors(() => createUserWithEmailAndPassword(auth, email, password))

export const signOut = () => withFriendlyErrors(() => firebaseSignOut(auth))

export const sendPasswordReset = (email: string) =>
  withFriendlyErrors(() => sendPasswordResetEmail(auth, email))

/** ID token for API calls (Firebase refreshes it automatically before it expires). */
export const getAccessTokenEffect = Effect.promise(async () => {
  const user = await getCurrentUser()
  return user ? await user.getIdToken() : null
})
