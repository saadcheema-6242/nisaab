import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { CopyIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ChatAskCard, parseSetup } from './components/chat-ask-card'
import { ChatFlashcardsCard } from './components/chat-flashcards-card'
import { ChatMindMapCard } from './components/chat-mind-map-card'
import { ChatQuizCard } from './components/chat-quiz-card'
import {
  ToolStatus,
  toolOutputId,
  toolOutputValue,
  toolRunning,
} from './components/tool-status'
import { ImageCredit } from '@/components/image-credit'
import { ChatStudyPlanCard } from './components/chat-study-plan-card'
import { ThinkingIndicator } from './components/thinking-indicator'
import { chatLang, stageLabel } from './chat-labels'
import { ChatPaperCard } from './components/chat-paper-card'
import { ChatInput } from './components/chat-input'
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import type {
  ChatMessageDto,
  FilePartDto,
  SourceDocumentPartDto,
  TextPartDto,
} from '@/integrations/api/client'
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation'
import { Message, MessageContent } from '@/components/ai-elements/message'
import { Response } from '@/components/ai-elements/response'
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from '@/components/ai-elements/sources'
import {
  chatAtom,
  chatStreamStatusAtom,
  streamMessageAtom,
} from '@/data-acess/chat'
import { projectAtom } from '@/data-acess/project'
// Simple ID generator
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

interface ChatbotProps {
  chatId: string
  projectId: string
  // Sent automatically when the chat is empty, e.g. "Explain SLO P-11-B-05"
  initialPrompt?: string
  onInitialPromptSent?: () => void
}

export const Chatbot: React.FC<ChatbotProps> = ({
  chatId,
  projectId,
  initialPrompt,
  onInitialPromptSent,
}) => {
  const [input, setInput] = useState('')
  // Ticked beside the message box. Empty means the tutor chooses, which is
  // how the chat behaved before there was a choice at all.
  const [tools, setTools] = useState<ReadonlyArray<string>>([])
  const [webSearch, setWebSearch] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const chatKey = `${projectId}:${chatId}`
  const chatResult = useAtomValue(chatAtom(chatKey))
  const streamStatus = useAtomValue(chatStreamStatusAtom(chatId))
  const streamMessage = useAtomSet(streamMessageAtom, {
    mode: 'promise',
  })

  const messages = Result.isSuccess(chatResult)
    ? (chatResult.value.messages ?? [])
    : []
  const isStreaming = streamStatus !== null

  // What to say while the student waits, in the language they chose
  const projectResult = useAtomValue(projectAtom(projectId))
  const lang = chatLang(
    Result.isSuccess(projectResult) ? projectResult.value.language_code : 'en',
  )
  const lastMessage = messages.at(-1)
  const streamingParts =
    isStreaming && lastMessage?.role === 'assistant'
      ? (lastMessage.parts ?? [])
      : []
  // A running tool says what it is doing on its own line, so show one indicator
  const toolSpeaking = streamingParts.some(
    (part) => part.type === 'tool_call' && toolRunning(part),
  )
  const writingText = streamingParts.some(
    (part) => part.type === 'text' && part.text_content.trim() !== '',
  )

  // Convert blob URL to data URL
  const blobToDataUrl = useCallback(
    async (blobUrl: string): Promise<string> => {
      const response = await fetch(blobUrl)
      const blob = await response.blob()
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result as string)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    },
    [],
  )

  const handleSubmit = async (message: PromptInputMessage) => {
    const hasText = Boolean(message.text)
    const hasAttachments = Boolean(message.files.length)
    if (!(hasText || hasAttachments)) {
      return
    }

    const parts: Array<TextPartDto | FilePartDto> = []

    // Process text part
    if (hasText) {
      parts.push({
        type: 'text',
        text_content: message.text,
        order: parts.length,
      })
    }

    // Process file attachments - convert to base64 data URLs
    const fileParts = await Promise.all(
      message.files.map(async (file) => {
        // If it's already a URL (from Azure), use it directly
        if (
          file.url &&
          !file.url.startsWith('blob:') &&
          !file.url.startsWith('data:')
        ) {
          return {
            type: 'file' as const,
            file_name: file.filename || 'file',
            file_type: file.mediaType,
            file_url: file.url,
            order: parts.length + message.files.indexOf(file),
          } as FilePartDto
        }

        // Convert blob URL to data URL if needed
        let dataUrl = file.url
        if (file.url?.startsWith('blob:')) {
          dataUrl = await blobToDataUrl(file.url)
        }

        if (!dataUrl || !dataUrl.startsWith('data:')) {
          throw new Error('Invalid file URL')
        }

        // Return file part with base64 data URL
        // The backend will upload it to blob storage and replace with SAS URL
        return {
          type: 'file' as const,
          file_name: file.filename || 'file',
          file_type: file.mediaType,
          file_url: dataUrl, // Base64 data URL - backend will handle upload
          order: parts.length + message.files.indexOf(file),
        } as FilePartDto
      }),
    )

    parts.push(...fileParts)

    // Create user message
    const userMessage: ChatMessageDto = {
      id: generateId(),
      chat_id: chatId,
      role: 'user',
      created_at: new Date().toISOString(),
      parts,
    }

    // Stream the message
    streamMessage({
      message: userMessage,
      projectId: projectId,
      chatId: chatId,
      tools,
      webSearch,
    })

    setInput('')
  }

  const initialPromptSent = useRef(false)
  useEffect(() => {
    if (
      !initialPrompt ||
      initialPromptSent.current ||
      !Result.isSuccess(chatResult) ||
      messages.length > 0 ||
      isStreaming
    ) {
      return
    }
    initialPromptSent.current = true
    handleSubmit({ text: initialPrompt, files: [] })
    onInitialPromptSent?.()
    // Runs once per chat; handleSubmit is recreated every render
  }, [initialPrompt, chatResult, messages.length, isStreaming])

  // Copy the answer as shown, with each formula once (KaTeX also renders a hidden
  // MathML copy of every formula for screen readers)
  const handleCopy = useCallback((elementId: string, fallback: string) => {
    const element = document.getElementById(elementId)
    if (!element) {
      navigator.clipboard.writeText(fallback)
      return
    }
    const clone = element.cloneNode(true) as HTMLElement
    clone.querySelectorAll('.katex-mathml').forEach((node) => node.remove())
    clone.style.position = 'fixed'
    clone.style.left = '-9999px'
    document.body.appendChild(clone)
    const text = clone.innerText
    clone.remove()
    navigator.clipboard.writeText(text.trim() || fallback)
  }, [])

  return (
    <div className="relative mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col">
      <Conversation className="min-h-0 flex-1">
        <ConversationContent>
          {messages.map((message: ChatMessageDto, messageIndex: number) => (
            <div key={message.id} className="space-y-2">
              {/* Render file attachments for user messages */}
              {message.role === 'user' &&
                message.parts &&
                message.parts.filter((part) => part.type === 'file').length >
                  0 && (
                  <Message from="user">
                    <MessageContent>
                      <div className="space-y-2">
                        {message.parts
                          .filter(
                            (part): part is FilePartDto => part.type === 'file',
                          )
                          .map((part: FilePartDto, i: number) =>
                            // A picture is shown, not named: the student sent
                            // it to be looked at, and the tutor can see it too.
                            part.file_type?.startsWith('image/') ? (
                              <a
                                key={`${message.id}-file-${i}`}
                                href={part.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block"
                              >
                                <img
                                  src={part.file_url}
                                  alt={part.file_name}
                                  className="max-h-64 w-auto rounded-lg border"
                                />
                              </a>
                            ) : (
                              <div
                                key={`${message.id}-file-${i}`}
                                className="flex items-center gap-2 p-2 bg-muted rounded"
                              >
                                <span className="text-sm">
                                  {part.file_name}
                                </span>
                                <a
                                  href={part.file_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-primary hover:underline"
                                >
                                  View
                                </a>
                              </div>
                            ),
                          )}
                      </div>
                    </MessageContent>
                  </Message>
                )}

              {/* Collect and render source-document parts together */}
              {message.parts &&
                (() => {
                  const sourceDocuments = message.parts.filter(
                    (p): p is SourceDocumentPartDto =>
                      p.type === 'source-document',
                  )
                  return sourceDocuments.length > 0 ? (
                    <Sources key={`${message.id}-sources`}>
                      <SourcesTrigger count={sourceDocuments.length} />
                      <SourcesContent>
                        {sourceDocuments.map((sourceDoc, idx) => {
                          // Build URL to view the document
                          // If we have a document_id in provider_metadata, we could link to it
                          // For now, we'll use a placeholder or the source_id
                          const documentUrl = sourceDoc.provider_metadata
                            ?.document_id
                            ? `/dashboard/p/${projectId}/d/${sourceDoc.provider_metadata.document_id}`
                            : `#${sourceDoc.source_id}`

                          return (
                            <Source
                              key={`${message.id}-source-${idx}`}
                              href={documentUrl}
                              title={
                                sourceDoc.title ||
                                sourceDoc.filename ||
                                'Document'
                              }
                            />
                          )
                        })}
                      </SourcesContent>
                    </Sources>
                  ) : null
                })()}

              {/* Render all parts except source-document (handled above) */}
              {(() => {
                const visibleParts = (message.parts ?? []).filter(
                  (part) => part.type !== 'source-document',
                )
                const isLastMessage = message.id === lastMessage?.id
                return visibleParts.map((part, i: number) => {
                  const isLastPart = i === visibleParts.length - 1
                  switch (part.type) {
                    case 'text':
                      return (
                        <Message
                          key={`${message.id}-${i}`}
                          from={message.role as 'user' | 'assistant' | 'system'}
                        >
                          <MessageContent>
                            <div id={`chat-text-${message.id}-${i}`}>
                              <Response
                                className={
                                  isStreaming &&
                                  isLastMessage &&
                                  isLastPart &&
                                  message.role === 'assistant'
                                    ? 'is-typing'
                                    : undefined
                                }
                              >
                                {part.text_content}
                              </Response>
                            </div>
                          </MessageContent>
                          {message.role === 'assistant' &&
                            isLastPart &&
                            !(isStreaming && isLastMessage) && (
                              <div className="flex gap-2 mt-2">
                                <button
                                  onClick={() =>
                                    handleCopy(
                                      `chat-text-${message.id}-${i}`,
                                      part.text_content,
                                    )
                                  }
                                  className="p-1 hover:bg-muted rounded"
                                  title="Copy"
                                >
                                  <CopyIcon className="size-3" />
                                </button>
                              </div>
                            )}
                        </Message>
                      )
                    case 'file':
                      // File parts are handled above in the user message section
                      return null
                    // case 'reasoning':
                    //   return (
                    //     <Reasoning
                    //       key={`${message.id}-part-${i}`}
                    //       className="w-full"
                    //       isStreaming={
                    //         isStreaming &&
                    //         i === (message.parts?.length || 0) - 1 &&
                    //         message.id === messages[messages.length - 1]?.id
                    //       }
                    //     >
                    //       <ReasoningTrigger />
                    //       <ReasoningContent>
                    //         {String(
                    //           (
                    //             part as {
                    //               text_content?: string
                    //               text?: string
                    //             }
                    //           ).text_content ||
                    //             (
                    //               part as {
                    //                 text_content?: string
                    //                 text?: string
                    //               }
                    //             ).text ||
                    //             '',
                    //         )}
                    //       </ReasoningContent>
                    //     </Reasoning>
                    //   )
                    case 'tool_call': {
                      // Practice started by the tutor is shown as a card to answer here
                      const quizId =
                        part.tool_name === 'practice_quiz'
                          ? toolOutputId(part, 'quiz_id')
                          : null
                      const groupId =
                        part.tool_name === 'practice_flashcards'
                          ? toolOutputId(part, 'group_id')
                          : null
                      const mindMapId =
                        part.tool_name === 'practice_mind_map'
                          ? toolOutputId(part, 'mind_map_id')
                          : null
                      const paperId =
                        part.tool_name === 'practice_paper'
                          ? toolOutputId(part, 'paper_id')
                          : null
                      const setup =
                        part.tool_name === 'ask_practice_questions'
                          ? parseSetup(part)
                          : null
                      // A figure the tutor drew by writing and running the
                      // code for it, so it needs no credit - unlike a found
                      // diagram, nobody else drew it. generate_image is
                      // here too: the image maker is gone and nothing new
                      // arrives from it, but chats that used it keep their
                      // pictures. The link is signed and lasts a week, so an
                      // old chat may lose it anyway.
                      const imageUrl =
                        part.tool_name === 'draw_figure' ||
                        part.tool_name === 'generate_image'
                          ? toolOutputId(part, 'image_url')
                          : null
                      const studyPlanId =
                        part.tool_name === 'make_study_plan'
                          ? toolOutputId(part, 'study_plan_id')
                          : null
                      // A real diagram found in an openly licensed
                      // collection. It must be shown with its credit.
                      const diagramUrl =
                        part.tool_name === 'find_diagram'
                          ? toolOutputId(part, 'image_url')
                          : null
                      return (
                        <div
                          key={`${message.id}-part-${i}`}
                          className="space-y-2"
                        >
                          <ToolStatus
                            toolCall={part}
                            projectId={projectId}
                            lang={lang}
                            showOpen={
                              !quizId &&
                              !groupId &&
                              !mindMapId &&
                              !paperId &&
                              !setup &&
                              !imageUrl &&
                              !diagramUrl &&
                              !studyPlanId
                            }
                          />
                          {setup && (
                            <ChatAskCard
                              setup={setup}
                              answered={messageIndex < messages.length - 1}
                              onAsk={(text) =>
                                handleSubmit({ text, files: [] })
                              }
                            />
                          )}
                          {studyPlanId && (
                            <ChatStudyPlanCard
                              projectId={projectId}
                              studyPlanId={studyPlanId}
                            />
                          )}
                          {quizId && (
                            <ChatQuizCard
                              projectId={projectId}
                              quizId={quizId}
                              onAsk={(text) =>
                                handleSubmit({ text, files: [] })
                              }
                            />
                          )}
                          {groupId && (
                            <ChatFlashcardsCard
                              projectId={projectId}
                              groupId={groupId}
                            />
                          )}
                          {paperId && (
                            <ChatPaperCard
                              projectId={projectId}
                              paperId={paperId}
                            />
                          )}
                          {imageUrl && (
                            <img
                              src={imageUrl}
                              alt={toolOutputId(part, 'alt') ?? 'Picture'}
                              className="w-full max-w-lg rounded-lg border bg-white"
                              loading="lazy"
                            />
                          )}
                          {diagramUrl && (
                            <figure className="w-full max-w-lg">
                              <img
                                src={diagramUrl}
                                alt={toolOutputId(part, 'alt') ?? 'Diagram'}
                                className="w-full rounded-lg border bg-white"
                                loading="lazy"
                              />
                              <figcaption className="mt-1">
                                <ImageCredit
                                  credit={toolOutputValue(part, 'credit')}
                                />
                              </figcaption>
                            </figure>
                          )}
                          {mindMapId && (
                            <ChatMindMapCard
                              projectId={projectId}
                              mindMapId={mindMapId}
                              onAsk={(text) =>
                                handleSubmit({ text, files: [] })
                              }
                            />
                          )}
                        </div>
                      )
                    }
                    // case 'source-url':
                    //   return (
                    //     <div
                    //       key={`${message.id}-part-${i}`}
                    //       className="bg-card text-card-foreground p-3 rounded-lg border-l-4 border-primary ring-1 ring-foreground/10"
                    //     >
                    //       <span className="text-xs text-muted-foreground font-medium">
                    //         Source URL:
                    //       </span>
                    //       <a
                    //         href={(part as { url?: string }).url}
                    //         target="_blank"
                    //         rel="noopener noreferrer"
                    //         className="block text-primary hover:text-primary/80 underline text-sm mt-1 underline-offset-4"
                    //       >
                    //         {(part as { url?: string }).url}
                    //       </a>
                    //     </div>
                    //   )
                    // source-document parts are handled above in the Sources component
                    default:
                      return null
                  }
                })
              })()}
            </div>
          ))}
          {isStreaming && !toolSpeaking && !writingText && (
            <ThinkingIndicator
              lang={lang}
              label={stageLabel(
                streamStatus === 'generating' ? 'writing' : 'thinking',
                lang,
              )}
            />
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
      <ChatInput
        value={input}
        onChange={setInput}
        status={isStreaming ? 'streaming' : 'ready'}
        onSubmit={handleSubmit}
        textareaRef={textareaRef}
        tools={tools}
        onToolsChange={setTools}
        webSearch={webSearch}
        onWebSearchChange={setWebSearch}
      />
    </div>
  )
}
