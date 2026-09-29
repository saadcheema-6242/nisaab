import { Link } from '@tanstack/react-router'
import {
  AlertCircleIcon,
  CheckCircle2Icon,
  ChevronRightIcon,
  Loader2Icon,
} from 'lucide-react'
import type { ToolCallPartDto } from '@/integrations/api/client'

type Labels = { running: string; done: string }

const ITEMS = {
  quiz: 'quiz',
  flashcards: 'flashcards',
  note: 'note',
  mindmap: 'mind map',
} as const

// Friendly text for the tutor's tools; the raw tool names mean nothing to students
const labelsFor = (name: string): Labels => {
  if (name === 'search_project_documents')
    return {
      running: 'Searching your documents…',
      done: 'Searched your documents',
    }
  if (name === 'ask_practice_questions')
    return {
      running: 'Thinking about your practice…',
      done: 'A few quick questions first',
    }
  if (name === 'practice_paper')
    return {
      running: 'Preparing your practice paper…',
      done: 'Your paper is ready',
    }
  if (name === 'practice_mind_map')
    return { running: 'Drawing your mind map…', done: 'Your mind map is ready' }
  if (name === 'practice_flashcards')
    return {
      running: 'Preparing your flashcards…',
      done: 'Your flashcards are ready',
    }
  if (name === 'practice_quiz')
    return { running: 'Preparing your quiz…', done: 'Your quiz is ready' }
  if (name === 'find_syllabus_slos')
    return {
      running: 'Checking the FBISE syllabus…',
      done: 'Checked the FBISE syllabus',
    }

  const [area, action = ''] = name.split(/_(.+)/)
  const item: string =
    (ITEMS as Record<string, string | undefined>)[area] ?? 'content'
  const plural = item.endsWith('s') ? item : `${item}s`
  if (action.startsWith('create'))
    return {
      running: `Making your ${item}…`,
      done: `${item.charAt(0).toUpperCase()}${item.slice(1)} ready`,
    }
  if (action.startsWith('delete'))
    return { running: `Deleting ${item}…`, done: `Deleted ${item}` }
  if (action.startsWith('update'))
    return { running: `Updating ${item}…`, done: `Updated ${item}` }
  return {
    running: `Looking at your ${plural}…`,
    done: `Checked your ${plural}`,
  }
}

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

export const ToolStatus = ({
  toolCall,
  projectId,
  showOpen = true,
}: {
  toolCall: ToolCallPartDto
  projectId: string
  showOpen?: boolean
}) => {
  const labels = labelsFor(toolCall.tool_name)
  const failed = toolCall.tool_state === 'output-error'
  const done = toolCall.tool_state === 'output-available'
  const target =
    done && showOpen
      ? openTarget(projectId, parseOutput(toolCall.tool_output))
      : null

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      {failed ? (
        <AlertCircleIcon className="size-4 text-destructive" />
      ) : done ? (
        <CheckCircle2Icon className="size-4 text-emerald-600" />
      ) : (
        <Loader2Icon className="size-4 animate-spin" />
      )}
      <span className={failed ? 'text-destructive' : undefined}>
        {failed
          ? 'Something went wrong, please try again'
          : done
            ? labels.done
            : labels.running}
      </span>
      {target && (
        <Link
          {...target}
          className="ml-1 inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium text-foreground hover:bg-accent"
        >
          Open
          <ChevronRightIcon className="size-3" />
        </Link>
      )}
    </div>
  )
}
