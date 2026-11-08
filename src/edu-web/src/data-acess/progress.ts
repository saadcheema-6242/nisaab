import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

// Not kept alive: refetched whenever the dashboard is opened, so it shows the latest practice
export const progressAtom = runtime.atom(
  Effect.fn(function* () {
    const { apiClient } = yield* ApiClientService
    return yield* apiClient.getProgressApiV1ProgressGet()
  }),
)

/**
 * The graphs tab: mastery over time, the FBISE cognitive levels, and streaks.
 *
 * A second atom rather than more fields on the one above, matching the two
 * routes. The overview is what loads when the page opens; this reads every
 * answer the student has ever recorded, and the tab most people never open
 * should not make the one they all do any slower.
 *
 * Called through the raw httpClient because the generated client is built by
 * a command that cannot run here yet. Nothing about this endpoint needs it:
 * there is nothing to pass, the server works it all out from the token.
 */
export const progressGraphsAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/progress/graphs')
    if (response.status < 200 || response.status >= 300) {
      return yield* Effect.fail(
        new Error(`Progress graphs unavailable (${response.status})`),
      )
    }
    return (yield* response.json) as ProgressGraphs
  }),
)

export type TrendPoint = {
  week_start: string
  mastery: number | null
  attempts: number
}

export type CognitiveLevel = {
  level: string
  name: string
  paper_weight: number
  mastery: number | null
  examined_count: number
  practised_count: number
}

export type WeakestLevel = {
  level: string
  name: string
  marks_at_stake: number
}

export type ActivityDay = { day: string; answers: number }

export type Consistency = {
  current_streak: number
  longest_streak: number
  days_practised: number
  answers_this_week: number
  last_day: string | null
  calendar: Array<ActivityDay>
}

export type SubjectGraphs = {
  project_id: string
  subject_code: string
  name: string
  mastery: number | null
  trend: Array<TrendPoint>
  cognitive: Array<CognitiveLevel>
  weakest_level: WeakestLevel | null
}

export type ProgressGraphs = {
  subjects: Array<SubjectGraphs>
  consistency: Consistency
  overall_trend: Array<TrendPoint>
}
