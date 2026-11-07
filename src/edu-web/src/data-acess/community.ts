import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Data, Effect } from 'effect'
import { runtime } from './runtime'
import type * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import { ApiClientService } from '@/integrations/api/http'

/**
 * The room a student shares with the rest of their class.
 *
 * Called through the raw httpClient rather than the generated client, because
 * the generated client is built from the OpenAPI schema by a command that
 * cannot run here yet. Nothing about these endpoints needs it: there is no
 * room id to pass, since the server works the room out from the student's own
 * profile.
 */

/**
 * The server said no.
 *
 * Effect's HttpClient hands back a 404 as an ordinary response, so a body of
 * {"detail":"..."} parses happily into whatever type the call claimed to
 * return and the failure only shows up later as a blank screen. The status is
 * checked here instead.
 */
export class CommunityUnavailable extends Data.TaggedError('CommunityUnavailable')<{
  readonly status: number
  readonly message: string
}> {}

/**
 * Pull the server's own wording out of an error body.
 *
 * It matters here more than elsewhere. "This looks like it contains a phone
 * number" tells a student exactly what to change; "something went wrong"
 * leaves them retyping the same post until they give up.
 */
const reasonFrom = (body: unknown, status: number): string => {
  const shaped = body as
    | { detail?: string; error?: { message?: string } }
    | undefined
  const said = shaped?.error?.message ?? shaped?.detail
  if (typeof said === 'string' && said.trim()) return said
  if (status === 429) return 'You have reached your posts for today.'
  return 'That did not go through. Try again in a moment.'
}

const expectOk = <TBody>(response: HttpClientResponse.HttpClientResponse) =>
  Effect.gen(function* () {
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new CommunityUnavailable({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    return (yield* response.json) as TBody
  })

/** For 204s, which have no body to read. */
const expectNoContent = (response: HttpClientResponse.HttpClientResponse) =>
  Effect.gen(function* () {
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new CommunityUnavailable({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
  })

export type CommunityAttachment = {
  id: string
  kind: 'image' | 'audio' | 'file'
  filename: string
  content_type: string
  size_bytes: number
  duration_seconds: number | null
  url: string
  download_url: string
}

export type CommunityPollOption = {
  id: string
  text: string
  votes: number
  percent: number
  is_mine: boolean
  is_winning: boolean
}

export type CommunityPoll = {
  question: string
  options: Array<CommunityPollOption>
  total_votes: number
  has_voted: boolean
}

export type CommunityPost = {
  id: string
  body: string
  author_name: string
  is_mine: boolean
  created_at: string
  attachments: Array<CommunityAttachment>
  poll: CommunityPoll | null
  reported_by_me: boolean
  replies: Array<CommunityPost>
}

export type CommunityWarning = {
  post_id: string
  message: string
  created_at: string
  is_support: boolean
}

export type CommunityRoom = {
  grade: number
  group_code: string
  room_name: string
  member_count: number
  posts: Array<CommunityPost>
  posts_left_today: number
  warnings: Array<CommunityWarning>
}

export const communityRoomAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/community')
    return yield* expectOk<CommunityRoom>(response)
  }),
)

export const addPostAtom = runtime.fn(
  Effect.fn(function* (input: {
    body: string
    parentId?: string
    pollQuestion?: string
    pollOptions?: Array<string>
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/community', {
      body: HttpBody.unsafeJson({
        body: input.body,
        parent_id: input.parentId ?? null,
        poll_question: input.pollQuestion ?? null,
        poll_options: input.pollOptions ?? null,
      }),
    })
    const post = yield* expectOk<CommunityPost>(response)
    // Read the room again rather than splicing the new post in by hand. Other
    // people have been posting while this one was being typed, and showing
    // only your own arrival makes a busy room look empty.
    registry.refresh(communityRoomAtom)
    return post
  }),
)

/**
 * A post with files on it.
 *
 * Multipart rather than JSON, so the bytes are not base64'd into a string
 * one and a third times their size. A 50MB photo would become 67MB of text
 * on a connection that was already the reason it took so long.
 */
export const addPostWithFilesAtom = runtime.fn(
  Effect.fn(function* (input: {
    body: string
    parentId?: string
    files: Array<File>
    durations?: Array<number | null>
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService

    const form = new FormData()
    form.append('body', input.body)
    if (input.parentId) form.append('parent_id', input.parentId)
    if (input.durations?.length) {
      form.append('durations', JSON.stringify(input.durations))
    }
    for (const file of input.files) form.append('files', file, file.name)

    const response = yield* httpClient.post('/api/v1/community/with-files', {
      body: HttpBody.formData(form),
    })
    const post = yield* expectOk<CommunityPost>(response)
    registry.refresh(communityRoomAtom)
    return post
  }),
)

export const deletePostAtom = runtime.fn(
  Effect.fn(function* (postId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(`/api/v1/community/${postId}`)
    yield* expectNoContent(response)
    registry.refresh(communityRoomAtom)
  }),
)

export const reportPostAtom = runtime.fn(
  Effect.fn(function* (input: {
    postId: string
    reason?: string
    note?: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post(
      `/api/v1/community/${input.postId}/report`,
      {
        body: HttpBody.unsafeJson({
          reason: input.reason ?? null,
          note: input.note ?? null,
        }),
      },
    )
    yield* expectNoContent(response)
    registry.refresh(communityRoomAtom)
  }),
)

export const voteAtom = runtime.fn(
  Effect.fn(function* (input: { postId: string; optionId: string }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post(
      `/api/v1/community/${input.postId}/vote/${input.optionId}`,
      { body: HttpBody.unsafeJson({}) },
    )
    const post = yield* expectOk<CommunityPost>(response)
    registry.refresh(communityRoomAtom)
    return post
  }),
)

export const dismissWarningsAtom = runtime.fn(
  Effect.fn(function* () {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/community/warnings/seen', {
      body: HttpBody.unsafeJson({}),
    })
    yield* expectNoContent(response)
    registry.refresh(communityRoomAtom)
  }),
)

// ---- what an administrator sees -------------------------------------------

export type ModerationReport = {
  reporter_name: string
  reason: string | null
  note: string | null
  created_at: string
}

export type ModerationItem = {
  post_id: string
  body: string
  room_name: string
  grade: number
  group_code: string
  author_id: string
  author_name: string
  author_email: string | null
  created_at: string
  finding: string | null
  finding_label: string
  confidence: number | null
  why: string | null
  severity: number
  is_urgent: boolean
  report_count: number
  reports: Array<ModerationReport>
  warned_at: string | null
  reviewed_at: string | null
  attachment_count: number
}

export type ModerationQueue = {
  items: Array<ModerationItem>
  urgent_count: number
  flagged_count: number
  reported_count: number
  unreviewed_count: number
}

export const moderationQueueAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/admin/moderation')
    return yield* expectOk<ModerationQueue>(response)
  }),
)

export const deleteAnyPostAtom = runtime.fn(
  Effect.fn(function* (postId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(`/api/v1/admin/moderation/${postId}`)
    yield* expectNoContent(response)
    registry.refresh(moderationQueueAtom)
  }),
)

export const clearPostAtom = runtime.fn(
  Effect.fn(function* (postId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post(
      `/api/v1/admin/moderation/${postId}/clear`,
      { body: HttpBody.unsafeJson({}) },
    )
    yield* expectNoContent(response)
    registry.refresh(moderationQueueAtom)
  }),
)
