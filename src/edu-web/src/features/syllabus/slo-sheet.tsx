import { useAtomSet } from '@effect-atom/atom-react'
import { useNavigate } from '@tanstack/react-router'
import {
  BookOpenIcon,
  Layers3Icon,
  ListChecksIcon,
  Loader2Icon,
  PenLineIcon,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import {
  assessmentForms,
  cognitiveLevelNames,
  masteryLevel,
  masteryStyles,
} from './slo-labels'
import { SloExplainer } from './slo-explainer'
import type { SloDto } from '@/integrations/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { createChatAtom } from '@/data-acess/chat'
import { createFlashcardGroupStreamAtom } from '@/data-acess/flashcard'
import { createQuizStreamAtom } from '@/data-acess/quiz'
import { createSrqAtom } from '@/data-acess/srq'
import { cn } from '@/lib/utils'

export const explainPrompt = (slo: SloDto) =>
  `Explain SLO ${slo.code}: "${slo.description}" the way my FBISE exam expects, with a worked example.`

type SloSheetProps = {
  projectId: string
  slo: SloDto | null
  onClose: () => void
}

type Action = 'explain' | 'practise' | 'flashcards' | 'srq'

export const SloSheet = ({ projectId, slo, onClose }: SloSheetProps) => {
  const navigate = useNavigate()
  const createChat = useAtomSet(createChatAtom, { mode: 'promise' })
  const createQuiz = useAtomSet(createQuizStreamAtom, { mode: 'promise' })
  const createFlashcards = useAtomSet(createFlashcardGroupStreamAtom, {
    mode: 'promise',
  })
  const createSrq = useAtomSet(createSrqAtom, { mode: 'promise' })
  const [busy, setBusy] = useState<Action | null>(null)

  const run = async (action: Action, task: (slo: SloDto) => Promise<void>) => {
    if (!slo || busy) return
    setBusy(action)
    try {
      await task(slo)
    } catch {
      toast.error('Something went wrong, please try again')
    } finally {
      setBusy(null)
    }
  }

  const handleExplain = () =>
    run('explain', async (target) => {
      const chat = await createChat({ projectId, title: `SLO ${target.code}` })
      navigate({
        to: '/dashboard/p/$projectId/c/$chatId',
        params: { projectId, chatId: chat.id },
        search: { ask: explainPrompt(target) },
      })
    })

  const handlePractise = () =>
    run('practise', async (target) => {
      const quizId = await createQuiz({
        projectId,
        quizId: '',
        questionCount: 10,
        sloCode: target.code,
      })
      navigate({
        to: '/dashboard/p/$projectId/q/$quizId',
        params: { projectId, quizId },
      })
    })

  const handleSrq = () =>
    run('srq', async (target) => {
      const question = await createSrq({ projectId, sloCode: target.code })
      navigate({
        to: '/dashboard/p/$projectId/srq/$questionId',
        params: { projectId, questionId: question.id },
      })
    })

  const handleFlashcards = () =>
    run('flashcards', async (target) => {
      const flashcardGroupId = await createFlashcards({
        projectId,
        groupId: '',
        flashcardCount: 12,
        sloCode: target.code,
      })
      navigate({
        to: '/dashboard/p/$projectId/f/$flashcardGroupId',
        params: { projectId, flashcardGroupId },
      })
    })

  const icon = (action: Action, Icon: typeof BookOpenIcon) =>
    busy === action ? (
      <Loader2Icon className="size-4 animate-spin" />
    ) : (
      <Icon className="size-4" />
    )

  const level = masteryLevel(slo?.mastery)
  const form = slo ? assessmentForms[slo.assessment_form] : null
  // Some subjects (e.g. Computer Science) follow the SLO with what students must
  // understand, know and be able to do, one line each
  const [headline = '', ...details] = slo ? slo.description.split('\n') : []

  return (
    <Sheet open={slo !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto pb-6 sm:max-w-lg">
        {slo && form && (
          <>
            <SheetHeader>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="font-mono">
                  {slo.code}
                </Badge>
                <Badge
                  variant={
                    slo.assessment_form === 'summative'
                      ? 'default'
                      : 'secondary'
                  }
                >
                  {form.label}
                </Badge>
              </div>
              <SheetTitle className="text-left text-base leading-snug">
                {headline}
              </SheetTitle>
              <SheetDescription className="text-left">
                {slo.domain_code} · {slo.domain_name}
                {slo.content_area && slo.content_area !== slo.domain_name
                  ? ` › ${slo.content_area}`
                  : ''}
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-5 px-4 text-sm">
              {details.length > 0 && (
                <div className="space-y-2">
                  {details.map((line) => {
                    const [lead, ...rest] = line.split(': ')
                    return rest.length > 0 ? (
                      <p key={line} className="text-muted-foreground">
                        <span className="font-medium text-foreground">
                          {lead}:
                        </span>{' '}
                        {rest.join(': ')}
                      </p>
                    ) : (
                      <p key={line} className="text-muted-foreground">
                        {line}
                      </p>
                    )
                  })}
                </div>
              )}
              <div>
                <div className="font-medium">Assessment</div>
                <p className="text-muted-foreground">{form.detail}</p>
              </div>

              {(slo.cognitive_levels ?? []).length > 0 && (
                <div>
                  <div className="font-medium">Cognitive level</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {(slo.cognitive_levels ?? []).map((code) => (
                      <Badge key={code} variant="secondary">
                        {code} · {cognitiveLevelNames[code]}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {slo.periods ? (
                <div>
                  <div className="font-medium">Teaching time</div>
                  <p className="text-muted-foreground">
                    {slo.periods} periods (40 minutes each)
                  </p>
                </div>
              ) : null}

              <div>
                <div className="font-medium">Your progress</div>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={cn(
                      'size-2.5 rounded-full',
                      masteryStyles[level].dot,
                    )}
                  />
                  <span className="text-muted-foreground">
                    {slo.mastery == null
                      ? 'Not practised yet'
                      : `${Math.round(slo.mastery * 100)}% · ${masteryStyles[level].label} (${slo.attempts} answers)`}
                  </span>
                </div>
              </div>

              <div className="grid gap-2 pt-2">
                <Button onClick={handleExplain} disabled={busy !== null}>
                  {icon('explain', BookOpenIcon)}
                  Explain this SLO
                </Button>
                <Button
                  variant="outline"
                  onClick={handlePractise}
                  disabled={busy !== null}
                >
                  {icon('practise', ListChecksIcon)}
                  Practise 10 MCQs
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSrq}
                  disabled={busy !== null}
                >
                  {icon('srq', PenLineIcon)}
                  Written answer (SRQ), marked by AI
                </Button>
                <Button
                  variant="outline"
                  onClick={handleFlashcards}
                  disabled={busy !== null}
                >
                  {icon('flashcards', Layers3Icon)}
                  Flashcards
                </Button>
              </div>

              <SloExplainer
                gradeSubjectId={slo.grade_subject_id}
                sloCode={slo.code}
              />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
