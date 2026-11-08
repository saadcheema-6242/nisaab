import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Data, Effect } from 'effect'
import { runtime } from './runtime'
import type * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import { ApiClientService } from '@/integrations/api/http'

/**
 * Weekly class sessions.
 *
 * Read through the raw httpClient rather than the generated client, as the
 * progress graphs do, because the generator is run by a command that cannot
 * run here yet. Nothing about these routes needs it: the server works out
 * who is asking from the token.
 */

export type Teacher = {
  id: string | null
  name: string
  headline: string | null
}

export type StudentSession = {
  id: string
  title: string
  description: string | null
  subject_code: string
  subject_name: string
  grade: number
  teacher: Teacher | null
  starts_at: string
  duration_minutes: number
  when: string
  state: 'upcoming' | 'open' | 'ended'
  /** Present only while the session is open. Withheld by the server, not hidden here. */
  join_url: string | null
}

export type TeacherSession = Omit<StudentSession, 'teacher'> & {
  groups: Array<string>
}

export type AdminSession = StudentSession & {
  meeting_source: string
  groups: Array<string>
  cancelled_at: string | null
}

export type TeacherOption = {
  id: string
  name: string
  email: string | null
  headline: string | null
}

const read = <TBody>(path: string, what: string) =>
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get(path)
    if (response.status < 200 || response.status >= 300) {
      return yield* Effect.fail(new Error(`${what} (${response.status})`))
    }
    return (yield* response.json) as TBody
  })

/** The student's own timetable. */
export const mySessionsAtom = runtime.atom(
  read<{ sessions: Array<StudentSession> }>(
    '/api/v1/sessions/mine',
    'Your sessions could not be loaded',
  ),
)

/** The classes this account is down to teach. Empty for a student. */
export const teachingAtom = runtime.atom(
  read<{
    teacher: Teacher
    next_session: TeacherSession | null
    sessions: Array<TeacherSession>
  }>('/api/v1/sessions/teaching', 'Your classes could not be loaded'),
)

/** Everything scheduled, plus who can be put in front of a class. */
export const allSessionsAtom = runtime.atom(
  read<{ sessions: Array<AdminSession>; teachers: Array<TeacherOption> }>(
    '/api/v1/sessions',
    'The timetable could not be loaded',
  ),
)

/**
 * The server's own wording matters here as much as it does in Community.
 * "Use a link from one of: meet.google.com, zoom.us, ..." tells an
 * administrator exactly what to fix; "Bad request" sends them guessing.
 */
export class SessionRefused extends Data.TaggedError('SessionRefused')<{
  readonly status: number
  readonly message: string
}> {}

const reasonFrom = (body: unknown, status: number): string => {
  const shaped = body as { detail?: string } | undefined
  if (typeof shaped?.detail === 'string' && shaped.detail.trim()) {
    return shaped.detail
  }
  if (status === 404) return 'That is no longer there.'
  return 'That did not go through. Try again in a moment.'
}

const expectOk = <TBody>(response: HttpClientResponse.HttpClientResponse) =>
  Effect.gen(function* () {
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new SessionRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    return (yield* response.json) as TBody
  })

export type NewSession = {
  title: string
  description?: string
  subjectCode: string
  grade: number
  /** ISO string in UTC. */
  startsAt: string
  durationMinutes: number
  joinUrl: string
  teacherId?: string
  teacherName?: string
}

export const scheduleSessionAtom = runtime.fn(
  Effect.fn(function* (input: NewSession) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/sessions', {
      body: HttpBody.unsafeJson({
        title: input.title,
        description: input.description ?? null,
        subject_code: input.subjectCode,
        grade: input.grade,
        starts_at: input.startsAt,
        duration_minutes: input.durationMinutes,
        join_url: input.joinUrl,
        teacher_id: input.teacherId ?? null,
        teacher_name: input.teacherName ?? null,
      }),
    })
    const made = yield* expectOk<AdminSession>(response)
    registry.refresh(allSessionsAtom)
    return made
  }),
)

export const cancelSessionAtom = runtime.fn(
  Effect.fn(function* (sessionId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(`/api/v1/sessions/${sessionId}`)
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new SessionRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    registry.refresh(allSessionsAtom)
  }),
)

export const setTeacherRoleAtom = runtime.fn(
  Effect.fn(function* (input: {
    userId: string
    role: 'student' | 'teacher'
    headline?: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.put(
      `/api/v1/sessions/teachers/${input.userId}`,
      {
        body: HttpBody.unsafeJson({
          role: input.role,
          headline: input.headline ?? null,
        }),
      },
    )
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new SessionRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    registry.refresh(allSessionsAtom)
  }),
)
