import { Result, useAtomValue } from '@effect-atom/atom-react'
import { DownloadMenu } from './download-menu'
import type { convertToTree } from '@/features/mind-map/components/mind-map-view'
import { flashcardGroupAtom, flashcardsAtom } from '@/data-acess/flashcard'
import { mindMapAtom } from '@/data-acess/mind-map'
import { noteAtom } from '@/data-acess/note'
import { paperAtom } from '@/data-acess/paper'
import { projectAtom } from '@/data-acess/project'
import { latestStudyPlanRemoteAtom } from '@/data-acess/study-plan'
import { currentUserAtom } from '@/data-acess/auth'
import {
  quizAtom,
  quizQuestionsAtom,
} from '@/data-acess/quiz'

// Each component loads its own data and offers the formats that suit it. The export
// code is imported only when a format is chosen, so it never slows the page down.

const useProjectName = (projectId: string) => {
  const result = useAtomValue(projectAtom(projectId))
  return Result.isSuccess(result) ? result.value.name : undefined
}

/** Passed through to DownloadMenu so a tight row can show just the icon. */
type MenuProps = { iconOnly?: boolean; autoOpen?: boolean }

const subtitleOf = (projectName?: string, sloCode?: string | null) =>
  [projectName, sloCode ? `SLO ${sloCode}` : null].filter(Boolean).join(' · ') || undefined

export const QuizDownload = ({
  projectId,
  quizId,
  ...menu
}: { projectId: string; quizId: string } & MenuProps) => {
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
      {...menu}
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
  ...menu
}: { projectId: string; groupId: string } & MenuProps) => {
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
      {...menu}
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
  ...menu
}: { projectId: string; mindMapId: string } & MenuProps) => {
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
      {...menu}
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

export const PaperDownload = ({
  projectId,
  paperId,
  ...menu
}: { projectId: string; paperId: string } & MenuProps) => {
  const result = useAtomValue(paperAtom(`${projectId}:${paperId}`))
  const projectName = useProjectName(projectId)
  // Anything but a paper still being written: a submitted paper is exactly when
  // the answers and solutions become worth exporting.
  if (!Result.isSuccess(result) || result.value.status === 'preparing') return null
  const paper = result.value
  const args = { paper, subtitle: projectName }
  const load = async () => (await import('@/lib/export/paper')).exportPaperPdf
  const attempted = Object.keys(paper.answers ?? {}).length > 0

  return (
    <DownloadMenu
      {...menu}
      options={[
        {
          label: 'PDF to attempt (no answers)',
          run: async () => (await load())({ ...args, mode: 'blank' }),
        },
        // Only worth offering once there is something of theirs to show
        ...(attempted || paper.result
          ? [
              {
                label: 'PDF with my answers',
                run: async () => (await load())({ ...args, mode: 'answers' }),
              },
            ]
          : []),
        // The correct answers only reach the browser after marking
        ...(paper.result
          ? [
              {
                label: 'PDF with full solutions',
                run: async () => (await load())({ ...args, mode: 'solutions' }),
              },
            ]
          : []),
      ]}
    />
  )
}

export const NoteDownload = ({
  projectId,
  noteId,
  ...menu
}: { projectId: string; noteId: string } & MenuProps) => {
  const result = useAtomValue(noteAtom(`${projectId}:${noteId}`))
  const projectName = useProjectName(projectId)
  if (!Result.isSuccess(result) || !result.value.content) return null
  const note = result.value
  return (
    <DownloadMenu
      {...menu}
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

export const StudyPlanDownload = ({
  projectId,
  ...menu
}: { projectId: string } & MenuProps) => {
  const result = useAtomValue(latestStudyPlanRemoteAtom(projectId))
  const userResult = useAtomValue(currentUserAtom)
  const projectName = useProjectName(projectId)
  if (!Result.isSuccess(result) || !result.value) return null
  const plan = result.value
  // Plans written before the plan became a day-by-day schedule have no steps,
  // so there is nothing worth exporting from them.
  if ((plan.content.items ?? []).length === 0) return null
  const studentName = Result.isSuccess(userResult)
    ? userResult.value.name || undefined
    : undefined
  return (
    <DownloadMenu
      {...menu}
      options={[
        {
          label: 'PDF',
          run: async () =>
            (await import('@/lib/export/study-plan')).exportStudyPlanPdf(
              plan,
              projectName,
              studentName,
            ),
        },
        {
          label: 'Word (.docx)',
          run: async () =>
            (await import('@/lib/export/study-plan')).exportStudyPlanDocx(
              plan,
              projectName,
              studentName,
            ),
        },
      ]}
    />
  )
}
