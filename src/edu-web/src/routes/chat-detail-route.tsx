import { useNavigate } from '@tanstack/react-router'
import { ChatPage } from '@/features/chat/chat-page'
import { chatDetailRoute } from '@/routes/_config'

export const ChatDetailRoute = () => {
  const params = chatDetailRoute.useParams()
  const search = chatDetailRoute.useSearch()
  const navigate = useNavigate()

  if (!params.chatId || !params.projectId) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
        <span>Invalid chat route</span>
      </div>
    )
  }

  return (
    <ChatPage
      projectId={params.projectId}
      chatId={params.chatId}
      initialPrompt={search?.ask}
      onInitialPromptSent={() =>
        navigate({
          to: '/dashboard/p/$projectId/c/$chatId',
          params,
          search: {},
          replace: true,
        })
      }
    />
  )
}
