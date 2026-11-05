import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import type * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import { Data, Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

/**
 * Account administration.
 *
 * Called through the raw httpClient rather than the generated client, which is
 * built by a command that cannot run here yet. Nothing on these endpoints
 * needs it.
 */

/**
 * The server said no, and said which no it was.
 *
 * Effect's HttpClient does not treat a 404 or a 403 as a failure: it hands
 * back the response and carries on. So {"detail":"Not found"} was parsed as a
 * user list, the page destructured an overview that was not there, and the
 * whole screen died with "Something went wrong". A status is checked now, and
 * the page is told what happened instead of being handed a lie.
 */
export class AdminRefused extends Data.TaggedError('AdminRefused')<{
  readonly status: number
}> {}

/** Reads one of these responses, or fails loudly. */
const expectOk = <A>(response: HttpClientResponse.HttpClientResponse) =>
  Effect.gen(function* () {
    if (response.status < 200 || response.status >= 300) {
      return yield* new AdminRefused({ status: response.status })
    }
    return (yield* response.json) as A
  })

export type AdminUsage = {
  chat_messages: number
  flashcard_generations: number
  quiz_generations: number
  mindmap_generations: number
  document_uploads: number
  last_reset: string | null
}

export type AdminUser = {
  id: string
  name: string | null
  email: string | null
  created_at: string
  grade: number | null
  group_code: string | null
  language: string | null
  onboarded: boolean
  ban_state: 'active' | 'temporary' | 'permanent'
  banned_until: string | null
  ban_reason: string | null
  banned_by: string | null
  usage: AdminUsage
  practice_answers: number
}

export type AdminUserDetail = AdminUser & {
  projects: number
  chats: number
  messages: number
  documents: number
  quizzes: number
  flashcard_groups: number
  notes: number
  mind_maps: number
  papers: number
  study_plans: number
  srq_attempts: number
  community_posts: number
  subjects: Array<string>
}

export type AdminOverview = {
  total_users: number
  onboarded_users: number
  banned_users: number
  active_today: number
  by_group: Record<string, number>
  by_grade: Record<string, number>
  practice_answers: number
}

export type AdminUserList = {
  overview: AdminOverview
  users: Array<AdminUser>
  total: number
}

export type DeletionReport = {
  user_id: string
  email: string | null
  deleted: Record<string, number>
  note: string
}

/** Whether the signed-in user may manage accounts. */
export const adminStateAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/admin/me')
    return yield* expectOk<{ is_admin: boolean }>(response)
  }),
)

export const adminUsersAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/admin/users?limit=200')
    return yield* expectOk<AdminUserList>(response)
  }),
)

export const adminUserAtom = runtime.fn(
  Effect.fn(function* (userId: string) {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get(`/api/v1/admin/users/${userId}`)
    return yield* expectOk<AdminUserDetail>(response)
  }),
)

export const banUserAtom = runtime.fn(
  Effect.fn(function* (input: {
    userId: string
    days: number | null
    reason: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post(
      `/api/v1/admin/users/${input.userId}/ban`,
      {
        body: HttpBody.unsafeJson({
          days: input.days,
          reason: input.reason,
        }),
      },
    )
    const user = yield* expectOk<AdminUser>(response)
    registry.refresh(adminUsersAtom)
    return user
  }),
)

export const unbanUserAtom = runtime.fn(
  Effect.fn(function* (userId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post(
      `/api/v1/admin/users/${userId}/unban`,
      { body: HttpBody.unsafeJson({}) },
    )
    const user = yield* expectOk<AdminUser>(response)
    registry.refresh(adminUsersAtom)
    return user
  }),
)

/**
 * Delete an account for good.
 *
 * The email is sent back to the server and checked there, not just in the
 * dialog. A confirmation that only the browser enforces is not a
 * confirmation.
 */
export const deleteUserAtom = runtime.fn(
  Effect.fn(function* (input: { userId: string; confirmEmail: string }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(
      `/api/v1/admin/users/${input.userId}?confirm_email=${encodeURIComponent(
        input.confirmEmail,
      )}`,
    )
    const report = yield* expectOk<DeletionReport>(response)
    registry.refresh(adminUsersAtom)
    return report
  }),
)

/**
 * Delete every account except your own.
 *
 * The expected count is sent so the server can refuse if it does not match.
 * A number read off a staging screen will not match production, and the
 * request is turned down rather than wiping the wrong database.
 */
export const deleteAllUsersAtom = runtime.fn(
  Effect.fn(function* (input: { confirm: string; expectedCount: number }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(
      `/api/v1/admin/users?confirm=${encodeURIComponent(input.confirm)}` +
        `&expected_count=${input.expectedCount}`,
    )
    const report = yield* expectOk<DeletionReport>(response)
    registry.refresh(adminUsersAtom)
    return report
  }),
)
