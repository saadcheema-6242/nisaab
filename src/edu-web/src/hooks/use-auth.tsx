import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAtomValue } from '@effect-atom/atom-react'
import { authAtom } from '@/data-acess/auth'
import {
  resendVerification,
  sendPasswordReset,
  signIn,
  signInWithGoogle,
  signOut,
  signUp,
} from '@/lib/auth-client'

export const useAuth = () => {
  const { session, user } = useAtomValue(authAtom)
  const queryClient = useQueryClient()

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      signIn(email, password),
    onError: (error) => {
      console.error('Login failed:', error)
    },
  })

  const passwordResetMutation = useMutation({
    mutationFn: (email: string) => sendPasswordReset(email),
    onError: (error) => {
      console.error('Password reset failed:', error)
    },
  })

  const signUpMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      signUp(email, password),
    onError: (error) => {
      console.error('Sign up failed:', error)
    },
  })

  const logoutMutation = useMutation({
    mutationFn: () => signOut(),
    onSuccess: () => {
      queryClient.clear()
    },
    onError: (error) => {
      console.error('Logout failed:', error)
    },
  })

  const getAccessToken = async () => {
    if (!user) return null
    return user.getIdToken()
  }

  // Google has already confirmed the address, so an account arriving this
  // way never meets the confirmation step.
  const googleMutation = useMutation({
    mutationFn: () => signInWithGoogle(),
    onError: (error) => {
      console.error('Google sign-in failed:', error)
    },
  })

  const resendMutation = useMutation({
    mutationFn: () => resendVerification(),
    onError: (error) => {
      console.error('Could not resend the verification email:', error)
    },
  })

  return {
    isAuthenticated: !!session && !!user,
    session,
    user,
    login: loginMutation.mutate,
    signUp: signUpMutation.mutate,
    signInWithGoogle: googleMutation.mutate,
    resendVerification: resendMutation.mutate,
    sendPasswordReset: passwordResetMutation.mutate,
    logout: logoutMutation.mutate,
    getAccessToken,
    isLoading:
      loginMutation.isPending ||
      logoutMutation.isPending ||
      signUpMutation.isPending ||
      googleMutation.isPending ||
      resendMutation.isPending ||
      passwordResetMutation.isPending,
    loginError: loginMutation.error,
    logoutError: logoutMutation.error,
    signUpError: signUpMutation.error,
    googleError: googleMutation.error,
    verificationSent: resendMutation.isSuccess,
    passwordResetError: passwordResetMutation.error,
    passwordResetSent: passwordResetMutation.isSuccess,
  }
}
