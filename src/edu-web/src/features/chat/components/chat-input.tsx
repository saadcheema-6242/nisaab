import React from 'react'
import { ChatToolsMenu } from './chat-tools-menu'
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from '@/components/ai-elements/prompt-input'

// What the + menu will take: a student's own notes, a past paper, a photo of
// a page. Anything else is refused before it is uploaded.
const UPLOAD_TYPES = [
  'image/*',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.docx',
].join(',')

type Props = {
  value: string
  onChange: (value: string) => void
  status: 'streaming' | 'error' | 'ready' | 'submitted'
  onSubmit: (message: PromptInputMessage) => void
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
  tools: ReadonlyArray<string>
  onToolsChange: (tools: ReadonlyArray<string>) => void
  webSearch: boolean
  onWebSearchChange: (on: boolean) => void
}

export const ChatInput: React.FC<Props> = ({
  value,
  onChange,
  status,
  onSubmit,
  textareaRef,
  tools,
  onToolsChange,
  webSearch,
  onWebSearchChange,
}) => {
  return (
    <PromptInput
      globalDrop
      multiple
      accept={UPLOAD_TYPES}
      onSubmit={onSubmit}
    >
      <PromptInputHeader>
        <PromptInputAttachments>
          {(attachment) => <PromptInputAttachment data={attachment} />}
        </PromptInputAttachments>
      </PromptInputHeader>
      <PromptInputBody>
        <PromptInputTextarea
          onChange={(e) => onChange(e.target.value)}
          ref={textareaRef}
          value={value}
        />
      </PromptInputBody>
      <PromptInputFooter>
        <PromptInputTools>
          <PromptInputActionMenu>
            <PromptInputActionMenuTrigger />
            <PromptInputActionMenuContent>
              <PromptInputActionAddAttachments />
            </PromptInputActionMenuContent>
          </PromptInputActionMenu>
          <ChatToolsMenu
            tools={tools}
            onToolsChange={onToolsChange}
            webSearch={webSearch}
            onWebSearchChange={onWebSearchChange}
          />
        </PromptInputTools>
        <PromptInputSubmit status={status} />
      </PromptInputFooter>
    </PromptInput>
  )
}
