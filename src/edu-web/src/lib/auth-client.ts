import { initializeApp } from 'firebase/app'
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
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

/**
 * Create the account and send the confirmation link in one go.
 *
 * The server refuses an unconfirmed address, so without this a student would
 * be signed up, turned away, and given no way to put it right - an account
 * that exists and cannot be used, with no email to explain why.
 *
 * A failure to send is not a failure to sign up. The account is real either
 * way, and the sign-in page can offer to send the link again; throwing here
 * would tell a student their registration failed when it did not.
 */
export const signUp = async (email: string, password: string) => {
  const credential = await withFriendlyErrors(() =>
    createUserWithEmailAndPassword(auth, email, password),
  )
  try {
    await sendEmailVerification(credential.user)
  } catch (error) {
    console.error('Could not send the verification email', error)
  }
  return credential
}

/** Send the confirmation link again, for a student who never got the first. */
export const resendVerification = () =>
  withFriendlyErrors(async () => {
    const user = auth.currentUser
    if (!user) throw new Error('Sign in first, then we can resend the link.')
    await sendEmailVerification(user)
  })

/**
 * Sign in with Google.
 *
 * Google has already confirmed the address, so these accounts arrive
 * verified and never meet the confirmation step at all.
 */
export const signInWithGoogle = () =>
  withFriendlyErrors(() => signInWithPopup(auth, new GoogleAuthProvider()))

export const signOut = () => withFriendlyErrors(() => firebaseSignOut(auth))

export const sendPasswordReset = (email: string) =>
  withFriendlyErrors(() => sendPasswordResetEmail(auth, email))

/** ID token for API calls (Firebase refreshes it automatically before it expires). */
export const getAccessTokenEffect = Effect.promise(async () => {
  const user = await getCurrentUser()
  return user ? await user.getIdToken() : null
})
