import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

/**
 * Account administration.
 *
 * Called through the raw httpClient rather than the generated client, which is
 * built by a command that cannot run here yet. Nothing on these endpoints
 * needs it.
 */

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
    return (yield* response.json) as { is_admin: boolean }
  }),
)

export const adminUsersAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/admin/users?limit=200')
    return (yield* response.json) as AdminUserList
  }),
)

export const adminUserAtom = runtime.fn(
  Effect.fn(function* (userId: string) {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get(`/api/v1/admin/users/${userId}`)
    return (yield* response.json) as AdminUserDetail
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
    const user = (yield* response.json) as AdminUser
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
    const user = (yield* response.json) as AdminUser
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
    const report = (yield* response.json) as DeletionReport
    registry.refresh(adminUsersAtom)
    return report
  }),
)
