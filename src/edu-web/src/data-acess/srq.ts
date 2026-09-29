import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

// Key: `${projectId}:${questionId}`
export const srqDetailAtom = Atom.family((input: string) => {
  const [projectId, questionId] = input.split(':')
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getSrqApiV1ProjectsProjectIdSrqQuestionIdGet(
        projectId,
        questionId,
      )
    }),
  )
})

export const createSrqAtom = runtime.fn(
  Effect.fn(function* (input: { projectId: string; sloCode: string }) {
    const { apiClient } = yield* ApiClientService
    return yield* apiClient.createSrqApiV1ProjectsProjectIdSrqPost(
      input.projectId,
      { slo_code: input.sloCode },
    )
  }),
)

export const markSrqAtom = runtime.fn(
  Effect.fn(function* (input: {
    projectId: string
    questionId: string
    answer: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { apiClient } = yield* ApiClientService
    const attempt =
      yield* apiClient.markSrqApiV1ProjectsProjectIdSrqQuestionIdMarkPost(
        input.projectId,
        input.questionId,
        { answer: input.answer },
      )
    registry.refresh(srqDetailAtom(`${input.projectId}:${input.questionId}`))
    return attempt
  }),
)
