import { Result, useAtomValue } from '@effect-atom/atom-react'
import { DownloadMenu } from './download-menu'
import type { convertToTree } from '@/features/mind-map/components/mind-map-view'
import { flashcardGroupAtom, flashcardsAtom } from '@/data-acess/flashcard'
import { mindMapAtom } from '@/data-acess/mind-map'
import { noteAtom } from '@/data-acess/note'
import { projectAtom } from '@/data-acess/project'
import { quizAtom, quizQuestionsAtom } from '@/data-acess/quiz'

// Each component loads its own data and offers the formats that suit it. The export
// code is imported only when a format is chosen, so it never slows the page down.

const useProjectName = (projectId: string) => {
  const result = useAtomValue(projectAtom(projectId))
  return Result.isSuccess(result) ? result.value.name : undefined
}

const subtitleOf = (projectName?: string, sloCode?: string | null) =>
  [projectName, sloCode ? `SLO ${sloCode}` : null].filter(Boolean).join(' · ') || undefined

export const QuizDownload = ({ projectId, quizId }: { projectId: string; quizId: string }) => {
  const key = `${projectId}:${quizId}`
  const quiz = useAtomValue(quizAtom(key))
  const questions = useAtomValue(quizQuestionsAtom(key))
  const projectName = useProjectName(projectId)
  if (!Result.isSuccess(quiz) || !Result.isSuccess(questions) || questions.value.length === 0) {
    return null
  }
  const args = {
    title: quiz.value.name,
    subtitle: subtitleOf(projectName, quiz.value.slo_code),
    questions: questions.value,
  }
  return (
    <DownloadMenu
      options={[
        {
          label: 'PDF with answer key',
          run: async () => (await import('@/lib/export/quiz')).exportQuizPdf(args),
        },
        {
          label: 'PDF questions only',
          run: async () =>
            (await import('@/lib/export/quiz')).exportQuizPdf({ ...args, withAnswers: false }),
        },
      ]}
    />
  )
}

export const FlashcardsDownload = ({
  projectId,
  groupId,
}: {
  projectId: string
  groupId: string
}) => {
  const key = `${projectId}:${groupId}`
  const group = useAtomValue(flashcardGroupAtom(key))
  const cards = useAtomValue(flashcardsAtom(key))
  if (!Result.isSuccess(group) || !Result.isSuccess(cards) || cards.value.length === 0) {
    return null
  }
  const title = group.value.name
  const sloCode = group.value.slo_code
  return (
    <DownloadMenu
      options={[
        {
          label: 'PDF (printable cards)',
          run: async () =>
            (await import('@/lib/export/flashcards')).exportFlashcardsPdf(title, cards.value),
        },
        {
          label: 'Images for sharing (ZIP)',
          run: async () =>
            (await import('@/lib/export/flashcards')).exportFlashcardImagesZip(
              title,
              cards.value,
              sloCode,
            ),
        },
        {
          label: 'First card as image',
          run: async () =>
            (await import('@/lib/export/flashcards')).exportFlashcardImage(
              title,
              cards.value,
              0,
              sloCode,
            ),
        },
      ]}
    />
  )
}

export const MindMapDownload = ({
  projectId,
  mindMapId,
}: {
  projectId: string
  mindMapId: string
}) => {
  const result = useAtomValue(mindMapAtom(`${projectId}:${mindMapId}`))
  if (!Result.isSuccess(result)) return null
  const mindMap = result.value
  const data = mindMap.map_data as {
    nodes: Parameters<typeof convertToTree>[0]
    edges: Parameters<typeof convertToTree>[1]
  }
  if (!data.nodes.length) return null
  return (
    <DownloadMenu
      options={[
        {
          label: 'Image (PNG)',
          run: async () =>
            (await import('@/lib/export/mind-map')).exportMindMapPng(mindMap.title, data.nodes, data.edges),
        },
        {
          label: 'PDF',
          run: async () =>
            (await import('@/lib/export/mind-map')).exportMindMapPdf(mindMap.title, data.nodes, data.edges),
        },
      ]}
    />
  )
}

export const NoteDownload = ({ projectId, noteId }: { projectId: string; noteId: string }) => {
  const result = useAtomValue(noteAtom(`${projectId}:${noteId}`))
  const projectName = useProjectName(projectId)
  if (!Result.isSuccess(result) || !result.value.content) return null
  const note = result.value
  return (
    <DownloadMenu
      options={[
        {
          label: 'PDF',
          run: async () =>
            (await import('@/lib/export/note')).exportNotePdf(note.title, note.content, projectName),
        },
      ]}
    />
  )
}
