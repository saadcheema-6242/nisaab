import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

/**
 * The room a student shares with the rest of their class.
 *
 * Called through the raw httpClient rather than the generated client, because
 * the generated client is built from the OpenAPI schema by a command that
 * cannot run here yet. Nothing about these two endpoints needs it: there is no
 * room id to pass, since the server works the room out from the student's own
 * profile.
 */

export type CommunityPost = {
  id: string
  body: string
  author_name: string
  is_mine: boolean
  created_at: string
  replies: Array<CommunityPost>
}

export type CommunityRoom = {
  grade: number
  group_code: string
  room_name: string
  member_count: number
  posts: Array<CommunityPost>
}

export const communityRoomAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/community')
    return (yield* response.json) as CommunityRoom
  }),
)

export const addPostAtom = runtime.fn(
  Effect.fn(function* (input: { body: string; parentId?: string }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/community', {
      body: HttpBody.unsafeJson({
        body: input.body,
        parent_id: input.parentId ?? null,
      }),
    })
    const post = (yield* response.json) as CommunityPost
    // Read the room again rather than splicing the new post in by hand. Other
    // people have been posting while this one was being typed, and showing
    // only your own arrival makes a busy room look empty.
    registry.refresh(communityRoomAtom)
    return post
  }),
)

export const deletePostAtom = runtime.fn(
  Effect.fn(function* (postId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    yield* httpClient.del(`/api/v1/community/${postId}`)
    registry.refresh(communityRoomAtom)
  }),
)
