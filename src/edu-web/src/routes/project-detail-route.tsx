import { projectDetailRoute } from '@/routes/_config'
import { ProjectDetailPage } from '@/features/project/project-detail-page'

export const ProjectDetailRoute = () => {
  const params = projectDetailRoute.useParams()
  const search = projectDetailRoute.useSearch()
  return (
    <ProjectDetailPage projectId={params.projectId} sloCode={search?.slo} />
  )
}
