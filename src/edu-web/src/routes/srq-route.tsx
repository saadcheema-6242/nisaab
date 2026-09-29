import { SrqPage } from '@/features/srq/srq-page'
import { srqRoute } from '@/routes/_config'

export const SrqRoute = () => {
  const params = srqRoute.useParams()
  return <SrqPage projectId={params.projectId} questionId={params.questionId} />
}
