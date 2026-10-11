import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { practiceHistoryAtom } from './quiz-attempt'
import { ApiClientService } from '@/integrations/api/http'

// Key: `${projectId}:${paperId}`
export const paperAtom = Atom.family((input: string) => {
  const [projectId, paperId] = input.split(':')
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getPaperApiV1ProjectsProjectIdPapersPaperIdGet(
        projectId,
        paperId,
      )
    }),
  )
})

export const createPaperAtom = runtime.fn(
  Effect.fn(function* (input: {
    projectId: string
    length: 'mini' | 'standard' | 'half' | 'board'
    topic?: string
  }) {
    const { apiClient } = yield* ApiClientService
    return yield* apiClient.createPaperApiV1ProjectsProjectIdPapersPost(
      input.projectId,
      { length: input.length, topic: input.topic },
    )
  }),
)

// Saves answers while the student works (fire and forget)
export const savePaperAnswersAtom = runtime.fn(
  Effect.fn(function* (input: {
    projectId: string
    paperId: string
    answers: Record<string, string>
  }) {
    const { apiClient } = yield* ApiClientService
    yield* apiClient.savePaperAnswersApiV1ProjectsProjectIdPapersPaperIdAnswersPut(
      input.projectId,
      input.paperId,
      { answers: input.answers },
    )
  }),
)

export const submitPaperAtom = runtime.fn(
  Effect.fn(function* (input: {
    projectId: string
    paperId: string
    answers: Record<string, string>
  }) {
    const registry = yield* Registry.AtomRegistry
    const { apiClient } = yield* ApiClientService
    const paper =
      yield* apiClient.submitPaperApiV1ProjectsProjectIdPapersPaperIdSubmitPost(
        input.projectId,
        input.paperId,
        { answers: input.answers },
      )
    registry.refresh(paperAtom(`${input.projectId}:${input.paperId}`))
    registry.refresh(practiceHistoryAtom(input.projectId))
    return paper
  }),
)
