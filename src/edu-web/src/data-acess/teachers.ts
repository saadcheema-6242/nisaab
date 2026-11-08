import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Data, Effect } from 'effect'
import { runtime } from './runtime'
import type * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import { ApiClientService } from '@/integrations/api/http'

/**
 * Teacher accounts: applying, waiting, and being approved.
 */

export class TeacherRefused extends Data.TaggedError('TeacherRefused')<{
  readonly status: number
  readonly message: string
}> {}

const reasonFrom = (body: unknown, status: number): string => {
  const shaped = body as { detail?: string } | undefined
  if (typeof shaped?.detail === 'string' && shaped.detail.trim()) {
    return shaped.detail
  }
  if (status === 404) return 'That account is no longer there.'
  return 'That did not go through. Try again in a moment.'
}

const expectOk = <TBody>(response: HttpClientResponse.HttpClientResponse) =>
  Effect.gen(function* () {
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new TeacherRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    return (yield* response.json) as TBody
  })

export type TeacherProfile = {
  subjects: Array<string>
  grades: Array<number>
  school: string | null
  about: string | null
  applied_at: string | null
}

export type TeacherAccount = {
  id: string
  name: string
  email: string | null
  headline: string | null
  approved: boolean
  approved_at: string | null
  profile: TeacherProfile | null
}

/**
 * Where this account must go before it can use the app.
 *
 * One call, not three. The router has to decide before any page renders,
 * and asking separately means guessing while the answers arrive: a teacher
 * awaiting approval would see a flash of the student dashboard on the way
 * to the waiting page.
 */
export type AccountState = {
  role: 'student' | 'teacher'
  is_admin: boolean
  onboarded: boolean
  teacher_approved: boolean
  send_to: '/onboarding' | '/awaiting-approval' | null
  teacher: TeacherAccount | null
}

export const accountStateAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/teachers/me')
    return yield* expectOk<AccountState>(response)
  }),
)

export const teacherQueueAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/teachers/queue')
    return yield* expectOk<{
      waiting: Array<TeacherAccount>
      approved: Array<TeacherAccount>
    }>(response)
  }),
)

export const applyAsTeacherAtom = runtime.fn(
  Effect.fn(function* (input: {
    subjects: Array<string>
    grades: Array<number>
    school?: string
    headline?: string
    about?: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/teachers/apply', {
      body: HttpBody.unsafeJson({
        subjects: input.subjects,
        grades: input.grades,
        school: input.school ?? null,
        headline: input.headline ?? null,
        about: input.about ?? null,
      }),
    })
    const made = yield* expectOk<TeacherAccount>(response)
    registry.refresh(accountStateAtom)
    return made
  }),
)

/** The way off the waiting page: go back to being a student. */
export const withdrawTeacherAtom = runtime.fn(
  Effect.fn(function* () {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/teachers/withdraw')
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new TeacherRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    registry.refresh(accountStateAtom)
  }),
)

export const decideTeacherAtom = runtime.fn(
  Effect.fn(function* (input: { userId: string; approve: boolean }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.put(
      `/api/v1/teachers/${input.userId}/decision`,
      { body: HttpBody.unsafeJson({ approve: input.approve }) },
    )
    const made = yield* expectOk<TeacherAccount>(response)
    registry.refresh(teacherQueueAtom)
    return made
  }),
)
