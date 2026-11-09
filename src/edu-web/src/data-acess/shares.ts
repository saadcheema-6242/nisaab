import { Registry } from '@effect-atom/atom-react'
import { HttpBody } from '@effect/platform'
import { Data, Effect } from 'effect'
import { runtime } from './runtime'
import type * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import { ApiClientService } from '@/integrations/api/http'

/**
 * Public, read-only links to a quiz or a paper.
 *
 * The share a student makes is read through the ordinary authenticated
 * client. The share a stranger opens is not: that page has no account,
 * so it uses plain fetch against the public route rather than the client
 * that attaches a token it does not have.
 */

export class ShareRefused extends Data.TaggedError('ShareRefused')<{
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
      return yield* new ShareRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    return (yield* response.json) as TBody
  })

export type Share = {
  id: string
  token: string
  kind: 'quiz' | 'paper'
  target_id: string
  title: string | null
  created_at: string
  opened_count: number
  /** "/s/{token}". Joined to the current origin by the page. */
  path: string
}

/** The whole link, built from wherever the app is being served. */
export const shareUrl = (share: Pick<Share, 'path'>): string =>
  `${window.location.origin}${share.path}`

export const mySharesAtom = runtime.atom(
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get('/api/v1/shares')
    return yield* expectOk<Array<Share>>(response)
  }),
)

export const createShareAtom = runtime.fn(
  Effect.fn(function* (input: {
    kind: 'quiz' | 'paper'
    target_id: string
    title?: string
  }) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.post('/api/v1/shares', {
      body: HttpBody.unsafeJson({
        kind: input.kind,
        target_id: input.target_id,
        title: input.title ?? null,
      }),
    })
    const made = yield* expectOk<Share>(response)
    registry.refresh(mySharesAtom)
    return made
  }),
)

export const revokeShareAtom = runtime.fn(
  Effect.fn(function* (shareId: string) {
    const registry = yield* Registry.AtomRegistry
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.del(`/api/v1/shares/${shareId}`)
    if (response.status < 200 || response.status >= 300) {
      const body = yield* Effect.orElseSucceed(response.json, () => undefined)
      return yield* new ShareRefused({
        status: response.status,
        message: reasonFrom(body, response.status),
      })
    }
    registry.refresh(mySharesAtom)
  }),
)

// ---- what a stranger sees -------------------------------------------

export type SharedQuestion = {
  id: string
  question_text: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_option: string
  explanation: string | null
  slo_code: string | null
  cognitive_level: string | null
  image_path: string | null
  image_alt: string | null
  image_credit: Record<string, unknown> | null
  option_images: Record<string, string> | null
}

export type SharedView = {
  kind: 'quiz' | 'paper'
  title: string | null
  shared_by: string
  shared_at: string
  description?: string | null
  slo_code?: string | null
  questions?: Array<SharedQuestion>
  total_marks?: number
  time_limit_minutes?: number
  sections?: Array<{
    id: string
    title: string
    items: Array<Record<string, unknown>>
  }>
}

/**
 * Read a shared link.
 *
 * Plain fetch, not the generated client and not the Effect http client:
 * both attach an Authorization header, and this page is opened by people
 * who have never signed in. Sending a stale or absent token to a public
 * route is how a working link starts returning 401 for the one audience
 * it exists for.
 */
export const readShare = async (token: string): Promise<SharedView> => {
  // The same origin the authenticated client uses; see integrations/api/http.
  const base = import.meta.env.VITE_SERVER_URL ?? 'http://localhost:8000'
  const response = await fetch(`${base}/api/v1/public/shares/${token}`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? 'This link has been withdrawn, or it never existed.'
        : 'That link could not be opened just now.',
    )
  }
  return (await response.json()) as SharedView
}
