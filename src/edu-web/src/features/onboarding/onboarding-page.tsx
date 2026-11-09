import { Result, useAtom, useAtomValue } from '@effect-atom/atom-react'
import { useNavigate } from '@tanstack/react-router'
import { CheckIcon, Loader2Icon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { TeacherSignup } from './teacher-signup'
import type { ReactNode } from 'react'
import type { ExplanationLanguage } from '@/lib/languages'
import { Button } from '@/components/ui/button'
import { completeOnboardingAtom, profileAtom } from '@/data-acess/profile'
import { accountStateAtom } from '@/data-acess/teachers'
import { brand } from '@/lib/brand'
import { explanationLanguages } from '@/lib/languages'
import { grades, groups } from '@/lib/subjects'
import { cn } from '@/lib/utils'

type Grade = (typeof grades)[number]['grade']
type Group = (typeof groups)[number]['code']

// The annual exam is held in spring; after June the next exam is next year
const defaultExamYear = () => {
  const now = new Date()
  return now.getMonth() >= 5 ? now.getFullYear() + 1 : now.getFullYear()
}

const Choice = ({
  selected,
  onClick,
  title,
  detail,
}: {
  selected: boolean
  onClick: () => void
  title: ReactNode
  detail: ReactNode
}) => (
  <button
    type="button"
    onClick={onClick}
    className={cn(
      'flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors',
      'hover:border-primary/60 hover:bg-accent/50',
      selected && 'border-primary bg-primary/5 ring-1 ring-primary',
    )}
  >
    <div className="flex-1">
      <div className="font-semibold">{title}</div>
      <div className="text-sm text-muted-foreground">{detail}</div>
    </div>
    <span
      className={cn(
        'flex size-6 shrink-0 items-center justify-center rounded-full border',
        selected && 'border-primary bg-primary text-primary-foreground',
      )}
    >
      {selected && <CheckIcon className="size-4" />}
    </span>
  </button>
)

const steps = ['Class', 'Group', 'Language'] as const

export const OnboardingPage = () => {
  const navigate = useNavigate()
  const profileResult = useAtomValue(profileAtom)
  const [result, completeOnboarding] = useAtom(completeOnboardingAtom, {
    mode: 'promise',
  })

  // Who is signing up. Null until answered, except for an administrator,
  // who is a student of every cohort as well as a teacher and goes straight
  // to picking a starting cohort. Asking them would be a question with no
  // meaningful answer.
  const accountResult = useAtomValue(accountStateAtom)
  const isAdmin =
    Result.isSuccess(accountResult) && accountResult.value.is_admin
  const [kind, setKind] = useState<'student' | 'teacher' | null>(null)
  const who = isAdmin ? 'student' : kind

  const [step, setStep] = useState(0)
  const [grade, setGrade] = useState<Grade | null>(null)
  const [group, setGroup] = useState<Group | null>(null)
  const [language, setLanguage] = useState<ExplanationLanguage>('en')
  const [finished, setFinished] = useState(false)

  // Start from the saved answers when changing an existing profile
  useEffect(() => {
    if (Result.isSuccess(profileResult) && profileResult.value.profile) {
      const profile = profileResult.value.profile
      setGrade(profile.grade as Grade)
      setGroup(profile.group_code)
      setLanguage(profile.explanation_language)
    }
  }, [profileResult])

  const canContinue =
    (step === 0 && grade !== null) ||
    (step === 1 && group !== null) ||
    step === 2

  const handleFinish = async () => {
    if (grade === null || group === null) return
    await completeOnboarding({
      grade,
      group_code: group,
      explanation_language: language,
      exam_year: defaultExamYear(),
    })
    setFinished(true)
  }

  // completeOnboarding refreshes its atoms but does not wait for them, so
  // navigating the moment it returns raced the refetch and the dashboard
  // guard sent the student straight back here.
  //
  // The wait is on accountStateAtom specifically, because that is the atom
  // the guard reads. Waiting on the profile instead - which is what this
  // did until now - watches the wrong answer settle and leaves anyway, so
  // the bounce came back as soon as the guard moved to a different atom.
  // One question, one source: if that ever stops being true, this breaks
  // again in exactly the same way.
  useEffect(() => {
    if (!finished) return
    if (!Result.isSuccess(accountResult)) return
    if (accountResult.value.send_to !== null) return
    navigate({ to: '/dashboard', replace: true })
  }, [finished, accountResult, navigate])

  if (who === null) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 py-10">
          <div className="mb-8">
            <div className="text-sm font-semibold text-primary">
              {brand.name}
            </div>
            <h1 className="mt-2 text-2xl font-semibold">
              Welcome. Who are you?
            </h1>
            <p className="mt-1 text-muted-foreground">
              This decides what NISAAB sets up for you.
            </p>
          </div>
          <div className="space-y-3">
            <Choice
              selected={false}
              onClick={() => setKind('student')}
              title="I am a student"
              detail="Studying FSc. You will pick your class and group next."
            />
            <Choice
              selected={false}
              onClick={() => setKind('teacher')}
              title="I am a teacher"
              detail="You will take weekly sessions. An administrator approves teacher accounts before they are activated."
            />
          </div>
        </div>
      </div>
    )
  }

  if (who === 'teacher') {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen max-w-lg flex-col px-4 py-10">
          <div className="mb-8">
            <div className="text-sm font-semibold text-primary">
              {brand.name}
            </div>
            <h1 className="mt-2 text-2xl font-semibold">
              Tell us what you teach
            </h1>
            <p className="mt-1 text-muted-foreground">
              An administrator reads this and approves your account.
            </p>
          </div>
          <TeacherSignup onBack={() => setKind(null)} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-lg flex-col px-4 py-10">
        <div className="mb-8">
          <div className="text-sm font-semibold text-primary">{brand.name}</div>
          <h1 className="mt-2 text-2xl font-semibold">
            Set up your FSc subjects
          </h1>
          <p className="mt-1 text-muted-foreground">
            Three quick questions so the tutor follows your FBISE syllabus.
          </p>
        </div>

        <ol className="mb-6 flex gap-2">
          {steps.map((name, index) => (
            <li key={name} className="flex-1">
              <div
                className={cn(
                  'h-1.5 rounded-full bg-muted',
                  index <= step && 'bg-primary',
                )}
              />
              <div
                className={cn(
                  'mt-1 text-xs text-muted-foreground',
                  index === step && 'font-medium text-foreground',
                )}
              >
                {index + 1}. {name}
              </div>
            </li>
          ))}
        </ol>

        <div className="flex-1 space-y-3">
          {step === 0 && (
            <>
              <h2 className="font-medium">Which class are you in?</h2>
              {grades.map((option) => (
                <Choice
                  key={option.grade}
                  selected={grade === option.grade}
                  onClick={() => setGrade(option.grade)}
                  title={option.name}
                  detail={option.detail}
                />
              ))}
            </>
          )}

          {step === 1 && (
            <>
              <h2 className="font-medium">Which group are you studying?</h2>
              {groups.map((option) => (
                <Choice
                  key={option.code}
                  selected={group === option.code}
                  onClick={() => setGroup(option.code)}
                  title={option.name}
                  detail={option.subjects}
                />
              ))}
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="font-medium">
                How should the tutor explain things?
              </h2>
              {explanationLanguages.map((option) => (
                <Choice
                  key={option.code}
                  selected={language === option.code}
                  onClick={() => setLanguage(option.code)}
                  title={option.name}
                  detail={option.hint}
                />
              ))}
              <p className="text-xs text-muted-foreground">
                Formulas and scientific terms always stay in English, as in your
                exam. You can change this later in Settings.
              </p>
            </>
          )}
        </div>

        <div className="mt-8 flex gap-3">
          {step > 0 && (
            <Button
              variant="outline"
              onClick={() => setStep(step - 1)}
              disabled={result.waiting || finished}
            >
              Back
            </Button>
          )}
          {step < steps.length - 1 ? (
            <Button
              className="flex-1"
              disabled={!canContinue}
              onClick={() => setStep(step + 1)}
            >
              Continue
            </Button>
          ) : (
            <Button
              className="flex-1"
              disabled={
                result.waiting || finished || grade === null || group === null
              }
              onClick={handleFinish}
            >
              {(result.waiting || finished) && (
                <Loader2Icon className="size-4 animate-spin" />
              )}
              Create my subjects
            </Button>
          )}
        </div>

        <p className="mt-8 text-center text-xs text-muted-foreground">
          {brand.notice}
        </p>
      </div>
    </div>
  )
}
