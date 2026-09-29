import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { practiceHistoryAtom } from './quiz-attempt'
import { ApiClientService } from '@/integrations/api/http'

// Key: `${projectId}:${groupId}`
export const latestFlashcardAttemptAtom = Atom.family((input: string) => {
  const [projectId, groupId] = input.split(':')
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      const res =
        yield* apiClient.getLatestFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsLatestGet(
          projectId,
          groupId,
        )
      return res.attempt ?? null
    }),
  )
})

// Records which cards the student knew, for SLO mastery
export const submitFlashcardAttemptAtom = runtime.fn(
  Effect.fn(function* (input: {
    projectId: string
    groupId: string
    knew: Record<string, boolean>
  }) {
    const registry = yield* Registry.AtomRegistry
    const { apiClient } = yield* ApiClientService
    const attempt =
      yield* apiClient.submitFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsPost(
        input.projectId,
        input.groupId,
        {
          results: Object.entries(input.knew).map(([flashcard_id, knew]) => ({
            flashcard_id,
            knew,
          })),
        },
      )
    registry.refresh(
      latestFlashcardAttemptAtom(`${input.projectId}:${input.groupId}`),
    )
    registry.refresh(practiceHistoryAtom(input.projectId))
    return attempt
  }),
)
