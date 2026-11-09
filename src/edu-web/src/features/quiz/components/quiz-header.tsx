import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, Share2Icon } from 'lucide-react'
import { useState } from 'react'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { ShareDialog } from '@/features/share/share-dialog'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { quizAtom } from '@/data-acess/quiz'
import { QuizDownload } from '@/components/downloads'

const QuizHeaderContent = ({
  quizId,
  projectId,
}: {
  quizId: string
  projectId: string
}) => {
  const quizResult = useAtomValue(quizAtom(`${projectId}:${quizId}`))

  return Result.builder(quizResult)
    .onSuccess((quiz) => (
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage className="line-clamp-1 font-medium">
              {quiz.name ?? 'Quiz'}
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    ))
    .onInitialOrWaiting(() => <Skeleton className="w-72 h-7" />)
    .onFailure(() => (
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage className="line-clamp-1 font-medium">
              Quiz
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    ))
    .render()
}

type QuizHeaderProps = {
  quizId: string
  projectId: string
}

export const QuizHeader = ({ quizId, projectId }: QuizHeaderProps) => {
  const quizResult = useAtomValue(quizAtom(`${projectId}:${quizId}`))
  const [sharing, setSharing] = useState(false)
  const name = Result.isSuccess(quizResult) ? quizResult.value.name : undefined

  return (
    <header className="bg-background sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b px-2">
      <div className="flex flex-1 items-center gap-2 px-3">
        {Result.isSuccess(quizResult) && (
          <>
            <SidebarTrigger />
            <Button variant="ghost" size="icon" className="size-7" asChild>
              <Link to="/dashboard/p/$projectId" params={{ projectId }}>
                <ArrowLeft className="size-4" />
                <span className="sr-only">Back to project</span>
              </Link>
            </Button>
          </>
        )}
        <Separator
          orientation="vertical"
          className="mr-2 data-[orientation=vertical]:h-4"
        />
        <QuizHeaderContent quizId={quizId} projectId={projectId} />
      </div>
      <div className="flex items-center gap-2 px-3">
        {/* Sharing sits next to downloading because they answer the same
            question - "get this out of the app" - and a student looking
            for one will look where the other is. */}
        <Button variant="ghost" size="sm" onClick={() => setSharing(true)}>
          <Share2Icon />
          <span className="sr-only sm:not-sr-only">Share</span>
        </Button>
        <QuizDownload projectId={projectId} quizId={quizId} />
      </div>
      <ShareDialog
        open={sharing}
        onOpenChange={setSharing}
        kind="quiz"
        targetId={quizId}
        title={name}
      />
    </header>
  )
}
