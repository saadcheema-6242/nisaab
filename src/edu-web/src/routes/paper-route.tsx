import { PaperPage } from '@/features/paper/paper-page'
import { paperRoute } from '@/routes/_config'

export const PaperRoute = () => {
  const params = paperRoute.useParams()
  return <PaperPage projectId={params.projectId} paperId={params.paperId} />
}
