import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Loader2Icon } from 'lucide-react'
import { Chatbot } from './chatbot'
import { ChatHeader } from './components/chat-header'
import { chatAtom } from '@/data-acess/chat'

type ChatPageProps = {
  projectId: string
  chatId: string
  initialPrompt?: string
  onInitialPromptSent?: () => void
}

export const ChatPage = ({
  projectId,
  chatId,
  initialPrompt,
  onInitialPromptSent,
}: ChatPageProps) => {
  const chatKey = `${projectId}:${chatId}`
  const chatResult = useAtomValue(chatAtom(chatKey))

  // Only the first load shows a spinner; a background reload keeps the chat on screen
  const isLoading = Result.isInitial(chatResult)
  const isError = Result.isFailure(chatResult)

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
        <Loader2Icon className="size-4 animate-spin" />
        <span>Loading chat...</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-destructive">
        <span>Failed to load chat</span>
      </div>
    )
  }

  return (
    // Exactly the screen height: only the messages scroll, the input stays in view
    <div className="flex h-svh flex-col overflow-hidden">
      <ChatHeader chatId={chatId} projectId={projectId} />

      <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden px-2 sm:px-4">
        <Chatbot
          chatId={chatId}
          projectId={projectId}
          initialPrompt={initialPrompt}
          onInitialPromptSent={onInitialPromptSent}
        />
      </div>
    </div>
  )
}
