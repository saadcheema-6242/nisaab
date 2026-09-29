import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { projectsRemoteAtom } from './project'
import { runtime } from './runtime'
import type {
  OnboardingRequest,
  ProfileUpdate,
} from '@/integrations/api/client'
import { ApiClientService } from '@/integrations/api/http'
import { withToast } from '@/lib/with-toast'

export const profileAtom = runtime
  .atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getProfileApiV1ProfileGet()
    }),
  )
  .pipe(Atom.keepAlive)

export const completeOnboardingAtom = runtime.fn(
  Effect.fn(
    function* (input: typeof OnboardingRequest.Encoded) {
      const registry = yield* Registry.AtomRegistry
      const { apiClient } = yield* ApiClientService
      const res = yield* apiClient.completeOnboardingApiV1OnboardingPost(input)
      registry.refresh(profileAtom)
      registry.refresh(projectsRemoteAtom)
      return res
    },
    withToast({
      onWaiting: () => 'Setting up your subjects...',
      onSuccess: 'Your subjects are ready',
      onFailure: 'Could not finish setup, please try again',
    }),
  ),
)

export const updateProfileAtom = runtime.fn(
  Effect.fn(
    function* (input: typeof ProfileUpdate.Encoded) {
      const registry = yield* Registry.AtomRegistry
      const { apiClient } = yield* ApiClientService
      const res = yield* apiClient.updateProfileApiV1ProfilePut(input)
      registry.refresh(profileAtom)
      registry.refresh(projectsRemoteAtom)
      return res
    },
    withToast({
      onWaiting: () => 'Saving...',
      onSuccess: 'Saved',
      onFailure: 'Could not save',
    }),
  ),
)
