import * as HttpClientRequest from '@effect/platform/HttpClientRequest'
import * as HttpClient from '@effect/platform/HttpClient'
import * as FetchHttpClient from '@effect/platform/FetchHttpClient'
import * as Effect from 'effect/Effect'
import * as Schedule from 'effect/Schedule'
import type * as HttpClientError from '@effect/platform/HttpClientError'
import { getAccessTokenEffect } from '@/lib/auth-client'
import * as ApiClient from '@/integrations/api/client'
import { NetworkMonitor } from '@/lib/network-monitor'

// Worth retrying: network failures (a cold-starting server answers without CORS headers,
// so the browser only sees a failed fetch) and "busy/unavailable" statuses
const RETRY_STATUSES = new Set([429, 502, 503, 504])
const isTransient = (error: HttpClientError.HttpClientError) =>
  error._tag === 'RequestError'
    ? error.reason === 'Transport'
    : RETRY_STATUSES.has(error.response.status)

export class ApiClientService extends Effect.Service<ApiClientService>()(
  'ApiClientService',
  {
    dependencies: [FetchHttpClient.layer, NetworkMonitor.Default],
    scoped: Effect.gen(function* () {
      const client = yield* HttpClient.HttpClient

      const httpClient = client.pipe(
        // Up to 4 retries over about 15 seconds, enough for a server cold start
        HttpClient.retry({
          while: isTransient,
          times: 4,
          schedule: Schedule.exponential('1 second'),
        }),
        HttpClient.mapRequestEffect(
          Effect.fn(function* (r) {
            const token = yield* getAccessTokenEffect
            return r.pipe(
              HttpClientRequest.setHeaders({
                Authorization: `Bearer ${token}`,
              }),
              HttpClientRequest.prependUrl(
                import.meta.env.VITE_SERVER_URL ?? 'http://localhost:8000',
              ),
            )
          }),
        ),
      )

      const apiClient = ApiClient.make(httpClient, {
        transformClient: Effect.fn(function* (c) {
          const token = yield* getAccessTokenEffect
          return c.pipe(
            HttpClient.mapRequest((r) =>
              r.pipe(
                HttpClientRequest.setHeaders({
                  Authorization: `Bearer ${token}`,
                }),
              ),
            ),
          )
        }),
      })

      return {
        httpClient,
        apiClient,
      }
    }),
  },
) {}
