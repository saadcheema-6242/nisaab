// @vitest-environment jsdom
import { Result } from '@effect-atom/atom-react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type * as AtomReact from '@effect-atom/atom-react'

// The profile the component reads, swapped between renders the way the real
// atom does when its refetch lands.
const state = vi.hoisted(() => ({
  profile: undefined as unknown,
  complete: vi.fn(() => Promise.resolve({})),
}))
const navigate = vi.hoisted(() => vi.fn())

vi.mock('@effect-atom/atom-react', async (importOriginal) => {
  const actual = await importOriginal<typeof AtomReact>()
  return {
    ...actual,
    useAtomValue: () => state.profile,
    useAtom: () => [{ waiting: false }, state.complete],
  }
})
vi.mock('@tanstack/react-router', () => ({ useNavigate: () => navigate }))
// brand reads the Firebase env, which tests do not carry
vi.mock('@/lib/brand', () => ({
  brand: { name: 'NISAAB', notice: 'Not an official FBISE product.' },
}))
vi.mock('@/data-acess/profile', () => ({
  profileAtom: {},
  completeOnboardingAtom: {},
}))

const { OnboardingPage } = await import('./onboarding-page')

const fresh = Result.success({ onboarded: false, profile: null })
const onboarded = Result.success({
  onboarded: true,
  profile: { grade: 11, group_code: 'PRE_MED', explanation_language: 'en' },
})

const answerEveryStep = () => {
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
  it('waits for the refreshed profile before going to the dashboard', async () => {
    state.profile = fresh
    const { rerender } = render(<OnboardingPage />)

    answerEveryStep()
    fireEvent.click(screen.getByRole('button', { name: /Create my subjects/ }))
    await vi.waitFor(() => expect(state.complete).toHaveBeenCalledOnce())

    // The save succeeded, but the profile atom still serves onboarded: false
    // while its refetch is in flight. Navigating now is what bounced the
    // student back here off the dashboard guard.
    rerender(<OnboardingPage />)
    expect(navigate).not.toHaveBeenCalled()

    // The refetch lands.
    state.profile = onboarded
    rerender(<OnboardingPage />)
    expect(navigate).toHaveBeenCalledWith({
      to: '/dashboard',
      replace: true,
    })
  })

  it('leaves a student who came back to change their answers alone', () => {
    state.profile = onboarded
    render(<OnboardingPage />)

    expect(navigate).not.toHaveBeenCalled()
  })
})
