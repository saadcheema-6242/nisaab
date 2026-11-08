/**
 * Scheduling the week, from the admin page.
 *
 * Two jobs: mark an account as a teacher, and put a teacher in front of a
 * class. No group is chosen, because a session belongs to a subject: one
 * Physics class serves Pre-Medical, Pre-Engineering and ICS together, and
 * the panel says so as the subject is picked rather than leaving it to be
 * discovered afterwards.
 *
 * The time is typed in Pakistan time, because that is the time the person
 * typing it is thinking in, and converted to UTC on the way out. Sending the
 * browser's own zone would be right here and wrong the moment anyone
 * schedules a class while travelling.
 */

import { useEffect, useState } from 'react'
import { Result, useAtom, useAtomValue } from '@effect-atom/atom-react'
import { Cause } from 'effect'
import { CalendarPlusIcon, Trash2Icon, UserPlusIcon } from 'lucide-react'
import type { AdminSession, TeacherOption } from '@/data-acess/sessions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  allSessionsAtom,
  cancelSessionAtom,
  scheduleSessionAtom,
} from '@/data-acess/sessions'

const PAKISTAN_OFFSET_MINUTES = 5 * 60

const SUBJECTS = [
  {
    code: 'PHY',
    name: 'Physics',
    groups: 'Pre-Medical, Pre-Engineering and ICS',
  },
  {
    code: 'CHEM',
    name: 'Chemistry',
    groups: 'Pre-Medical and Pre-Engineering',
  },
  { code: 'BIO', name: 'Biology', groups: 'Pre-Medical only' },
  { code: 'MATH', name: 'Mathematics', groups: 'Pre-Engineering and ICS' },
  { code: 'CS', name: 'Computer Science', groups: 'ICS only' },
]

/**
 * "2026-11-12T17:00" typed as Pakistan time, as a UTC instant.
 *
 * Deliberately not `new Date(local)`, which reads the string in whatever
 * zone the browser happens to be in. The class is at five o'clock in Lahore
 * whether it was scheduled from Lahore or from anywhere else.
 */
const toUtcIso = (local: string): string => {
  const [date, time] = local.split('T')
  const [y, m, d] = date.split('-').map(Number)
  const [hh, mm] = time.split(':').map(Number)
  const asUtc = Date.UTC(y, m - 1, d, hh, mm)
  return new Date(asUtc - PAKISTAN_OFFSET_MINUTES * 60_000).toISOString()
}

const ScheduleForm = ({ teachers }: { teachers: Array<TeacherOption> }) => {
  const [title, setTitle] = useState('')
  const [subjectCode, setSubject] = useState('PHY')
  const [grade, setGrade] = useState(11)
  const [when, setWhen] = useState('')
  const [duration, setDuration] = useState(60)
  const [joinUrl, setJoinUrl] = useState('')
  const [teacherId, setTeacherId] = useState('')
  const [teacherName, setTeacherName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  const [result, schedule] = useAtom(scheduleSessionAtom)

  // The setter does not reject: a failing Effect lands in the Result, so a
  // try/catch around it is dead code and the server's refusal is lost. That
  // caught us twice in Community; read it from the Result instead.
  //
  // In an effect, not during render. Calling setState while rendering is
  // how this component would re-render itself in a loop the moment a
  // request failed.
  useEffect(() => {
    if (!sent || result.waiting) return
    if (result._tag === 'Failure') {
      // squash returns unknown: the failure can be a defect as well as a
      // typed error, and only one of those carries a message.
      const thrown: unknown = Cause.squash(result.cause)
      setError(
        thrown instanceof Error && thrown.message
          ? thrown.message
          : 'That did not go through. Try again in a moment.',
      )
      setSent(false)
      return
    }
    if (result._tag === 'Success') {
      setTitle('')
      setWhen('')
      setJoinUrl('')
      setTeacherName('')
      setError(null)
      setSent(false)
    }
  }, [sent, result._tag, result.waiting])

  const chosen = SUBJECTS.find((s) => s.code === subjectCode)

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!when) {
      setError('Pick a date and time.')
      return
    }
    setSent(true)
    schedule({
      title,
      subjectCode,
      grade,
      startsAt: toUtcIso(when),
      durationMinutes: duration,
      joinUrl,
      teacherId: teacherId || undefined,
      teacherName: teacherName.trim() || undefined,
    })
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="s-title">Title</Label>
          <Input
            id="s-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Waves revision before the test"
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-subject">Subject</Label>
          <select
            id="s-subject"
            value={subjectCode}
            onChange={(e) => setSubject(e.target.value)}
            className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
          >
            {SUBJECTS.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name}
              </option>
            ))}
          </select>
          {chosen && (
            <p className="text-muted-foreground text-xs">
              Open to {chosen.groups}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-grade">Class</Label>
          <select
            id="s-grade"
            value={grade}
            onChange={(e) => setGrade(Number(e.target.value))}
            className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
          >
            <option value={11}>Class 11 (first year)</option>
            <option value={12}>Class 12 (second year)</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-when">Starts (Pakistan time)</Label>
          <Input
            id="s-when"
            type="datetime-local"
            value={when}
            onChange={(e) => setWhen(e.target.value)}
            required
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-duration">Minutes</Label>
          <Input
            id="s-duration"
            type="number"
            min={10}
            max={240}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
          />
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="s-link">Meeting link</Label>
          <Input
            id="s-link"
            value={joinUrl}
            onChange={(e) => setJoinUrl(e.target.value)}
            placeholder="https://meet.google.com/abc-defg-hij"
            required
          />
          <p className="text-muted-foreground text-xs">
            Google Meet, Zoom, Teams or Webex. Students only see it from fifteen
            minutes before the class starts.
          </p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-teacher">Teacher</Label>
          <select
            id="s-teacher"
            value={teacherId}
            onChange={(e) => setTeacherId(e.target.value)}
            className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
          >
            <option value="">Not signed up yet — type a name</option>
            {teachers.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {!teacherId && (
          <div className="space-y-1.5">
            <Label htmlFor="s-teacher-name">Teacher's name</Label>
            <Input
              id="s-teacher-name"
              value={teacherName}
              onChange={(e) => setTeacherName(e.target.value)}
              placeholder="Prof. Muhammad Tashfeen Qamar"
            />
            <p className="text-muted-foreground text-xs">
              You can timetable someone before they have an account.
            </p>
          </div>
        )}
      </div>

      {error && (
        <p className="rounded-md border border-red-300 bg-red-50 p-2.5 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </p>
      )}

      <Button type="submit" disabled={result.waiting}>
        <CalendarPlusIcon className="mr-1.5 size-4" />
        {result.waiting ? 'Scheduling…' : 'Schedule the class'}
      </Button>
    </form>
  )
}

const Scheduled = ({ sessions }: { sessions: Array<AdminSession> }) => {
  const [result, cancel] = useAtom(cancelSessionAtom)
  const [asking, setAsking] = useState<string | null>(null)

  if (sessions.length === 0) {
    return (
      <p className="text-muted-foreground py-6 text-sm">
        Nothing scheduled yet.
      </p>
    )
  }

  return (
    <ul className="divide-y">
      {sessions.map((one) => (
        <li key={one.id} className="flex flex-wrap items-center gap-3 py-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{one.title}</span>
              {one.cancelled_at && (
                <Badge variant="destructive">Cancelled</Badge>
              )}
              {one.state === 'open' && !one.cancelled_at && (
                <Badge className="bg-emerald-600 hover:bg-emerald-600">
                  Live
                </Badge>
              )}
              {one.state === 'ended' && (
                <Badge variant="secondary">Finished</Badge>
              )}
            </div>
            <p className="text-muted-foreground text-sm">
              {one.subject_name} · Class {one.grade} · {one.when}
              {one.teacher ? ` · ${one.teacher.name}` : ' · no teacher named'}
            </p>
          </div>
          {!one.cancelled_at &&
            one.state !== 'ended' &&
            (asking === one.id ? (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs">
                  Call it off?
                </span>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={result.waiting}
                  onClick={() => {
                    cancel(one.id)
                    setAsking(null)
                  }}
                >
                  Yes, cancel
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setAsking(null)}
                >
                  Keep it
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setAsking(one.id)}
                aria-label={`Cancel ${one.title}`}
              >
                <Trash2Icon className="size-4" />
              </Button>
            ))}
        </li>
      ))}
    </ul>
  )
}

export const SessionsPanel = () => {
  const result = useAtomValue(allSessionsAtom)

  if (Result.isFailure(result)) {
    return (
      <Card>
        <CardContent className="text-muted-foreground py-10 text-center text-sm">
          The timetable could not be loaded.
        </CardContent>
      </Card>
    )
  }
  if (!Result.isSuccess(result)) {
    return <p className="text-muted-foreground p-6 text-sm">Loading…</p>
  }

  const { sessions, teachers } = result.value

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Schedule a class</CardTitle>
        </CardHeader>
        <CardContent>
          {teachers.length === 0 && (
            <p className="mb-4 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-2.5 text-xs dark:border-amber-900 dark:bg-amber-950/40">
              <UserPlusIcon className="mt-0.5 size-4 shrink-0" />
              <span>
                No accounts are marked as teachers yet. You can still timetable
                a class by typing a teacher's name, and link the account later
                from the Accounts tab.
              </span>
            </p>
          )}
          <ScheduleForm teachers={teachers} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            The timetable ({sessions.filter((s) => s.state !== 'ended').length}{' '}
            upcoming)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Scheduled sessions={sessions} />
        </CardContent>
      </Card>
    </div>
  )
}
