import { Atom, Registry } from '@effect-atom/atom-react'
import { Effect } from 'effect'
import { runtime } from './runtime'
import type { ContentReview } from '@/integrations/api/client'
import { ApiClientService } from '@/integrations/api/http'

export const reviewerStateAtom = runtime
  .atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getReviewerStateApiV1ReviewMeGet()
    }),
  )
  .pipe(Atom.keepAlive)

export type ReviewFilter = {
  gradeSubjectId: string
  domainCode?: string
  kind?: string
  reviewStatus?: string
}

// Key: JSON of ReviewFilter
export const reviewItemsAtom = Atom.family((key: string) => {
  const filter = JSON.parse(key) as ReviewFilter
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.listReviewItemsApiV1ReviewItemsGet({
        grade_subject_id: filter.gradeSubjectId,
        domain_code: filter.domainCode,
        kind: filter.kind,
        review_status: filter.reviewStatus,
      })
    }),
  )
})

export const reviewSummaryAtom = Atom.family((gradeSubjectId: string) =>
  runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.reviewSummaryApiV1ReviewSummaryGet({
        grade_subject_id: gradeSubjectId,
      })
    }),
  ),
)

export const reviewItemAtom = runtime.fn(
  Effect.fn(function* (
    input: { itemId: string; gradeSubjectId: string } & typeof ContentReview.Encoded,
  ) {
    const registry = yield* Registry.AtomRegistry
    const { apiClient } = yield* ApiClientService
    const res = yield* apiClient.reviewItemApiV1ReviewItemsItemIdPatch(input.itemId, {
      review_status: input.review_status,
      review_note: input.review_note,
    })
    registry.refresh(reviewSummaryAtom(input.gradeSubjectId))
    return res
  }),
)
