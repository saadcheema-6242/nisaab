// @vitest-environment jsdom
import { Result } from '@effect-atom/atom-react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type * as AtomReact from '@effect-atom/atom-react'

// Two atoms, swapped between renders the way the real ones do when their
// refetches land. They are kept apart here because the bug this file exists
// to catch is the page watching the wrong one of them: a mock that answers
// every atom with the same value cannot see that mistake, and the earlier
// version of this test could not.
const PROFILE_ATOM = { id: 'profile' }
const ACCOUNT_ATOM = { id: 'account' }

const state = vi.hoisted(() => ({
  profile: undefined as unknown,
  account: undefined as unknown,
  complete: vi.fn(() => Promise.resolve({})),
}))
const navigate = vi.hoisted(() => vi.fn())

vi.mock('@effect-atom/atom-react', async (importOriginal) => {
  const actual = await importOriginal<typeof AtomReact>()
  return {
    ...actual,
    useAtomValue: (atom: unknown) =>
      atom === ACCOUNT_ATOM ? state.account : state.profile,
    useAtom: () => [{ waiting: false }, state.complete],
  }
})
vi.mock('@tanstack/react-router', () => ({ useNavigate: () => navigate }))
// brand reads the Firebase env, which tests do not carry
vi.mock('@/lib/brand', () => ({
  brand: { name: 'NISAAB', notice: 'Not an official FBISE product.' },
}))
vi.mock('@/data-acess/profile', () => ({
  profileAtom: PROFILE_ATOM,
  completeOnboardingAtom: {},
}))
vi.mock('@/data-acess/teachers', () => ({
  accountStateAtom: ACCOUNT_ATOM,
  applyAsTeacherAtom: {},
}))

const { OnboardingPage } = await import('./onboarding-page')

const fresh = Result.success({ onboarded: false, profile: null })
const onboarded = Result.success({
  onboarded: true,
  profile: { grade: 11, group_code: 'PRE_MED', explanation_language: 'en' },
})

/** What /teachers/me says before and after the profile exists. */
const sentHere = Result.success({
  role: 'student',
  is_admin: false,
  onboarded: false,
  teacher_approved: false,
  send_to: '/onboarding',
  teacher: null,
})
const letThrough = Result.success({
  role: 'student',
  is_admin: false,
  onboarded: true,
  teacher_approved: false,
  send_to: null,
  teacher: null,
})

const answerEveryStep = () => {
  // Onboarding now asks who you are first. Everything after it is the
  // student path exactly as it was, which is what the rest of this walk
  // through is checking.
  fireEvent.click(screen.getByText('I am a student'))
  fireEvent.click(screen.getByText('Class XI'))
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  fireEvent.click(screen.getByText('Pre-Medical'))
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
  fireEvent.click(screen.getByText('English'))
}

afterEach(() => {
  cleanup()
  navigate.mockClear()
  state.complete.mockClear()
})

describe('onboarding redirect', () => {
  it('waits for the guard to agree before going to the dashboard', async () => {
    state.profile = fresh
    state.account = sentHere
    const { rerender } = render(<OnboardingPage />)

    answerEveryStep()
    fireEvent.click(screen.getByRole('button', { name: /Create my subjects/ }))
    await vi.waitFor(() => expect(state.complete).toHaveBeenCalledOnce())

    // The save succeeded, but both atoms are still serving what they held
    // before it. Navigating now is what bounced the student back here off
    // the dashboard guard.
    rerender(<OnboardingPage />)
    expect(navigate).not.toHaveBeenCalled()

    // The profile lands first. This is the regression: the page used to
    // leave on this, while the guard - which reads the account state, not
    // the profile - still said "/onboarding" and sent them straight back,
    // for ever. Refreshing the profile is NOT permission to go.
    state.profile = onboarded
    rerender(<OnboardingPage />)
    expect(navigate).not.toHaveBeenCalled()

    // The atom the guard actually reads lands. Now, and only now.
    state.account = letThrough
    rerender(<OnboardingPage />)
    expect(navigate).toHaveBeenCalledWith({
      to: '/dashboard',
      replace: true,
    })
  })

  it('leaves a student who came back to change their answers alone', () => {
    state.profile = onboarded
    state.account = letThrough
    render(<OnboardingPage />)

    expect(navigate).not.toHaveBeenCalled()
  })
})
