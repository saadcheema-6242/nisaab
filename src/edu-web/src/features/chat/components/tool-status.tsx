import { Link } from '@tanstack/react-router'
import { AlertCircleIcon, CheckCircle2Icon, ChevronRightIcon } from 'lucide-react'
import { errorLabel, openLabel, stageLabel, toolLabels } from '../chat-labels'
import type { ChatLang } from '../chat-labels'
import type { ToolCallPartDto } from '@/integrations/api/client'
import { ThinkingDots } from '@/components/ui/thinking-dots'
import { useSlowAfter } from '@/hooks/use-slow-after'

type OpenTarget =
  | {
      to: '/dashboard/p/$projectId/q/$quizId'
      params: { projectId: string; quizId: string }
    }
  | {
      to: '/dashboard/p/$projectId/f/$flashcardGroupId'
      params: { projectId: string; flashcardGroupId: string }
    }
  | {
      to: '/dashboard/p/$projectId/n/$noteId'
      params: { projectId: string; noteId: string }
    }
  | {
      to: '/dashboard/p/$projectId/m/$mindMapId'
      params: { projectId: string; mindMapId: string }
    }

// Where the item a tool created can be opened
const openTarget = (projectId: string, output: unknown): OpenTarget | null => {
  if (!output || typeof output !== 'object') return null
  const o = output as Record<string, unknown>
  const id = (key: string) => (typeof o[key] === 'string' ? o[key] : null)
  const quizId = id('quiz_id')
  if (quizId)
    return {
      to: '/dashboard/p/$projectId/q/$quizId',
      params: { projectId, quizId },
    }
  const groupId = id('group_id')
  if (groupId)
    return {
      to: '/dashboard/p/$projectId/f/$flashcardGroupId',
      params: { projectId, flashcardGroupId: groupId },
    }
  const noteId = id('note_id')
  if (noteId)
    return {
      to: '/dashboard/p/$projectId/n/$noteId',
      params: { projectId, noteId },
    }
  const mindMapId = id('mind_map_id')
  if (mindMapId)
    return {
      to: '/dashboard/p/$projectId/m/$mindMapId',
      params: { projectId, mindMapId },
    }
  return null
}

export const parseOutput = (
  output: ToolCallPartDto['tool_output'],
): unknown => {
  if (typeof output === 'string' && output.trim().startsWith('{')) {
    try {
      return JSON.parse(output)
    } catch {
      return output
    }
  }
  return output
}

/** A string field from a finished tool's output, e.g. the quiz a tool created. */
export const toolOutputId = (toolCall: ToolCallPartDto, key: string) => {
  if (toolCall.tool_state !== 'output-available') return null
  const output = parseOutput(toolCall.tool_output)
  if (!output || typeof output !== 'object') return null
  const value = (output as Record<string, unknown>)[key]
  return typeof value === 'string' ? value : null
}

/** A tool's output under `key`, whatever shape it is - a credit is an object. */
export const toolOutputValue = (toolCall: ToolCallPartDto, key: string) => {
  if (toolCall.tool_state !== 'output-available') return null
  const output = parseOutput(toolCall.tool_output)
  if (!output || typeof output !== 'object') return null
  return (output as Record<string, unknown>)[key] ?? null
}

/** Whether a tool is still running, so the chat can show one indicator and not two. */
export const toolRunning = (toolCall: ToolCallPartDto) =>
  toolCall.tool_state !== 'output-available' &&
  toolCall.tool_state !== 'output-error'

export const ToolStatus = ({
  toolCall,
  projectId,
  lang = 'en',
  showOpen = true,
}: {
  toolCall: ToolCallPartDto
  projectId: string
  lang?: ChatLang
  showOpen?: boolean
}) => {
  const labels = toolLabels(toolCall.tool_name, lang)
  const failed = toolCall.tool_state === 'output-error'
  const done = toolCall.tool_state === 'output-available'
  const slow = useSlowAfter()
  const target =
    done && showOpen
      ? openTarget(projectId, parseOutput(toolCall.tool_output))
      : null

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {failed ? (
          <AlertCircleIcon className="size-4 text-destructive" />
        ) : done ? (
          <CheckCircle2Icon className="size-4 text-emerald-600" />
        ) : (
          <ThinkingDots className="px-0.5" label={labels.running} />
        )}
        <span
          dir="auto"
          className={
            failed
              ? 'text-destructive'
              : done
                ? undefined
                : 'thinking-text'
          }
        >
          {failed ? errorLabel(lang) : done ? labels.done : labels.running}
        </span>
        {target && (
          <Link
            {...target}
            className="ml-1 inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium text-foreground hover:bg-accent"
          >
            {openLabel(lang)}
            <ChevronRightIcon className="size-3" />
          </Link>
        )}
      </div>
      {!done && !failed && slow && (
        <p dir="auto" className="text-xs text-muted-foreground/80">
          {stageLabel('slow', lang)}
        </p>
      )}
    </div>
  )
}
