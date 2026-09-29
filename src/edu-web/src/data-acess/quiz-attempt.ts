import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

// Every finished quiz, flashcard run and paper in a workspace, newest first
export const practiceHistoryAtom = Atom.family((projectId: string) =>
  runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.listPracticeHistoryApiV1ProjectsProjectIdAttemptsGet(
        projectId,
      )
    }),
  ),
)

// The latest attempt (null before the first) and every attempt, first to last.
// Key: `${projectId}:${quizId}`
export const latestQuizAttemptAtom = Atom.family((input: string) => {
  const [projectId, quizId] = input.split(':')
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      const res =
        yield* apiClient.getLatestQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsLatestGet(
          projectId,
          quizId,
        )
      return { attempt: res.attempt ?? null, history: res.history ?? [] }
    }),
  )
})

// Scores the quiz on the server and records the answers for SLO mastery.
// Every submission is kept as a new attempt (Attempt 1, 2, ...).
export const submitQuizAttemptAtom = runtime
  .fn(
    Effect.fn(function* (input: {
      projectId: string
      quizId: string
      answers: Record<string, string | null>
    }) {
      const registry = yield* Registry.AtomRegistry
      const { apiClient } = yield* ApiClientService
      const attempt =
        yield* apiClient.submitQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsPost(
          input.projectId,
          input.quizId,
          {
            answers: Object.entries(input.answers).map(
              ([question_id, option]) => ({
                question_id,
                option,
              }),
            ),
          },
        )
      registry.refresh(
        latestQuizAttemptAtom(`${input.projectId}:${input.quizId}`),
      )
      registry.refresh(practiceHistoryAtom(input.projectId))
      return attempt
    }),
  )
  .pipe(Atom.keepAlive)
