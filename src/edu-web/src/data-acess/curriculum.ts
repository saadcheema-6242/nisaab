import { Atom } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

export const gradeSubjectsAtom = runtime
  .atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.listGradeSubjectsApiV1CurriculumGradeSubjectsGet()
    }),
  )
  .pipe(Atom.keepAlive)

export const curriculumTreeAtom = Atom.family((gradeSubjectId: string) =>
  runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getCurriculumTreeApiV1CurriculumGradeSubjectsGradeSubjectIdTreeGet(
        gradeSubjectId,
      )
    }),
  ),
)

// Key: `${gradeSubjectId}:${sloCode}`
export const sloExplainerAtom = Atom.family((input: string) => {
  const [gradeSubjectId, code] = input.split(':')
  return runtime
    .atom(
      Effect.fn(function* () {
        const { apiClient } = yield* ApiClientService
        const res =
          yield* apiClient.getSloExplainerApiV1CurriculumGradeSubjectsGradeSubjectIdSlosCodeExplainerGet(
            gradeSubjectId,
            code,
          )
        return res.explainer ?? null
      }),
    )
    .pipe(Atom.keepAlive)
})
