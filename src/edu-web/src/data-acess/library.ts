import { Effect } from 'effect'
import { runtime } from './runtime'
import { ApiClientService } from '@/integrations/api/http'

/**
 * History and Library: a student's work seen across every subject at
 * once, rather than one workspace at a time.
 */

export type HistoryKind =
  | 'quiz'
  | 'paper'
  | 'flashcards'
  | 'note'
  | 'mind_map'
  | 'study_plan'

export type HistoryItem = {
  id: string
  kind: HistoryKind
  name: string
  created_at: string | null
  project_id: string
  project_name?: string
  subject_code: string | null
  subject_name: string | null
  grade: number | null
  count?: number
  slo_code?: string | null
  status?: string
  total_marks?: number
}

export type SubjectTab = { code: string; name: string }

export type DocumentItem = {
  id: string
  file_name: string
  file_type: string
  file_size: number
  status: string
  summary: string | null
  uploaded_at: string | null
  project_id: string
  project_name?: string
  subject_code: string | null
  subject_name: string | null
}

const read = <TBody>(path: string) =>
  Effect.fn(function* () {
    const { httpClient } = yield* ApiClientService
    const response = yield* httpClient.get(path)
    if (response.status < 200 || response.status >= 300) {
      return yield* Effect.fail(new Error('Could not load that just now.'))
    }
    return (yield* response.json) as TBody
  })

export const historyAtom = runtime.atom(
  read<{ items: Array<HistoryItem>; subjects: Array<SubjectTab> }>(
    '/api/v1/library/history',
  ),
)

export const documentsAtom = runtime.atom(
  read<{ items: Array<DocumentItem>; subjects: Array<SubjectTab> }>(
    '/api/v1/library/documents',
  ),
)
