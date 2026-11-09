import { Atom, Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Effect } from 'effect'
import { projectsRemoteAtom } from './project'
import { runtime } from './runtime'
import { accountStateAtom } from './teachers'
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
      // The one the router asks. Without this the student finished setup,
      // was sent to the dashboard, and the guard - still holding the answer
      // from before they had a profile - sent them straight back here, for
      // ever. Refreshing the profile alone was not enough once the guard
      // stopped reading the profile.
      registry.refresh(accountStateAtom)
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

/**
 * Moving to another FSc group.
 *
 * Through the raw httpClient because the generated client is built by a
 * command that cannot run here yet. Both the profile and the project list are
 * refreshed afterwards: the group decides which subjects exist, so the
 * sidebar is wrong until it is read again.
 */
export const groupChangePreviewAtom = runtime.fn(
  Effect.fn(function* (groupCode: string) {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get(
      `/api/v1/profile/group-change?group_code=${encodeURIComponent(groupCode)}`,
    )
    return (yield* response.json) as {
      summary: string
      current_group: string | null
    }
  }),
)

export const changeGroupAtom = runtime.fn(
  Effect.fn(
    function* (groupCode: string) {
      const registry = yield* Registry.AtomRegistry
      const { httpClient } = yield* ApiClientService
      yield* httpClient.post('/api/v1/profile/group', {
        body: HttpBody.unsafeJson({ group_code: groupCode }),
      })
      registry.refresh(profileAtom)
      registry.refresh(projectsRemoteAtom)
    },
    withToast({
      onWaiting: () => 'Moving you to the new group...',
      onSuccess: 'Your subjects have been updated',
      onFailure: 'Could not change your group, please try again',
    }),
  ),
)
