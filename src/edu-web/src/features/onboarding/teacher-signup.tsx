/**
 * Signing up as a teacher.
 *
 * Shorter than the student path, because a teacher has no year or group of
 * their own: they say what they teach, not what they study. Nothing here
 * grants anything. The account is marked as a teacher claim and goes to the
 * waiting page until an administrator agrees.
 */

import { useEffect, useState } from 'react'
import { useAtom } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { applyAsTeacherAtom } from '@/data-acess/teachers'
import { cn } from '@/lib/utils'

const SUBJECTS = [
  { code: 'PHY', name: 'Physics' },
  { code: 'CHEM', name: 'Chemistry' },
  { code: 'BIO', name: 'Biology' },
  { code: 'MATH', name: 'Mathematics' },
  { code: 'CS', name: 'Computer Science' },
]

const YEARS = [
  { grade: 11, name: 'Class 11', detail: 'First year, HSSC-I' },
  { grade: 12, name: 'Class 12', detail: 'Second year, HSSC-II' },
]

const Pill = ({
  selected,
  onClick,
  children,
}: {
  selected: boolean
  onClick: () => void
  children: React.ReactNode
}) => (
  <button
    type="button"
    aria-pressed={selected}
    onClick={onClick}
    className={cn(
      'rounded-full border px-3.5 py-1.5 text-sm transition-colors',
      selected
        ? 'border-primary bg-primary text-primary-foreground'
        : 'hover:bg-muted',
    )}
  >
    {children}
  </button>
)

export const TeacherSignup = ({ onBack }: { onBack: () => void }) => {
  const [subjects, setSubjects] = useState<Array<string>>([])
  const [grades, setGrades] = useState<Array<number>>([])
  const [school, setSchool] = useState('')
  const [headline, setHeadline] = useState('')
  const [about, setAbout] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  const [result, apply] = useAtom(applyAsTeacherAtom)

  // Read the outcome from the Result, in an effect. The setter does not
  // reject, so a try/catch around it never runs and the server's refusal is
  // thrown away silently. That mistake has been made three times in this
  // codebase; the shape below is the one that works.
  useEffect(() => {
    if (!sent || result.waiting) return
    if (result._tag === 'Failure') {
      const thrown: unknown = Cause.squash(result.cause)
      setError(
        thrown instanceof Error && thrown.message
          ? thrown.message
          : 'That did not go through. Try again in a moment.',
      )
      setSent(false)
    }
    // On success the account state refreshes and the router moves us to the
    // waiting page, so there is nothing to do here.
  }, [sent, result._tag, result.waiting])

  const toggle = <T,>(list: Array<T>, value: T): Array<T> =>
    list.includes(value) ? list.filter((x) => x !== value) : [...list, value]

  const ready = subjects.length > 0 && grades.length > 0

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setSent(true)
    apply({
      subjects,
      grades,
      school: school.trim() || undefined,
      headline: headline.trim() || undefined,
      about: about.trim() || undefined,
    })
  }

  return (
    <form onSubmit={submit} className="flex-1 space-y-6">
      <div className="space-y-2">
        <h2 className="font-medium">Which subjects do you teach?</h2>
        <div className="flex flex-wrap gap-2">
          {SUBJECTS.map((subject) => (
            <Pill
              key={subject.code}
              selected={subjects.includes(subject.code)}
              onClick={() => setSubjects(toggle(subjects, subject.code))}
            >
              {subject.name}
            </Pill>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="font-medium">Which years?</h2>
        <div className="flex flex-wrap gap-2">
          {YEARS.map((year) => (
            <Pill
              key={year.grade}
              selected={grades.includes(year.grade)}
              onClick={() => setGrades(toggle(grades, year.grade))}
            >
              {year.name}
            </Pill>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="t-headline">Your title</Label>
        <Input
          id="t-headline"
          value={headline}
          onChange={(e) => setHeadline(e.target.value)}
          placeholder="MSc Physics, 12 years teaching"
        />
        <p className="text-muted-foreground text-xs">
          Students see this under your name on a session.
        </p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="t-school">Where you teach</Label>
        <Input
          id="t-school"
          value={school}
          onChange={(e) => setSchool(e.target.value)}
          placeholder="Islamabad Model College for Boys G-10/4"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="t-about">Anything else</Label>
        <textarea
          id="t-about"
          value={about}
          onChange={(e) => setAbout(e.target.value)}
          rows={3}
          maxLength={600}
          placeholder="Optional. This is what the administrator reads when deciding."
          className="border-input bg-background w-full rounded-md border p-2.5 text-sm"
        />
      </div>

      {error && (
        <p className="rounded-md border border-red-300 bg-red-50 p-2.5 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </p>
      )}

      <div className="flex gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button type="submit" disabled={!ready || result.waiting} className="flex-1">
          {result.waiting ? 'Sending…' : 'Send for approval'}
        </Button>
      </div>
      {!ready && (
        <p className="text-muted-foreground text-xs">
          Choose at least one subject and one year.
        </p>
      )}
    </form>
  )
}
