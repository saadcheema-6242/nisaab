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
