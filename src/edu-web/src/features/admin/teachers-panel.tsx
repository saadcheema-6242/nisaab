/**
 * Approving teachers.
 *
 * Anyone can sign up and say they teach Physics, so this queue is the only
 * thing between that claim and a stranger standing in front of a class.
 * What they said about themselves is shown in full, because approving a
 * name alone is approving nothing anyone can judge.
 *
 * Refusing is not a rejection: the account becomes an ordinary student and
 * the application goes. Somebody refused once can still use NISAAB, which
 * is the right outcome, and a row marked "rejected" for ever is not
 * something anybody acts on.
 */

import { useState } from 'react'
import { Result, useAtom, useAtomValue } from '@effect-atom/atom-react'
import { CheckIcon, ClockIcon, GraduationCapIcon, XIcon } from 'lucide-react'
import type { TeacherAccount } from '@/data-acess/teachers'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { decideTeacherAtom, teacherQueueAtom } from '@/data-acess/teachers'

const SUBJECT_NAMES: Record<string, string> = {
  PHY: 'Physics',
  CHEM: 'Chemistry',
  BIO: 'Biology',
  MATH: 'Mathematics',
  CS: 'Computer Science',
}

const describe = (teacher: TeacherAccount) => {
  const profile = teacher.profile
  if (!profile) return 'No application on file'
  const subjects = profile.subjects
    .map((code) => SUBJECT_NAMES[code] ?? code)
    .join(', ')
  const years = profile.grades.map((g) => `Class ${g}`).join(' and ')
  return `${subjects} · ${years}`
}

const Waiting = ({ teacher }: { teacher: TeacherAccount }) => {
  const [result, decide] = useAtom(decideTeacherAtom)
  const [refusing, setRefusing] = useState(false)

  return (
    <li className="space-y-3 py-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{teacher.name}</span>
            <Badge variant="secondary">Waiting</Badge>
          </div>
          {teacher.email && (
            <p className="text-muted-foreground text-sm">{teacher.email}</p>
          )}
          <p className="text-sm">{describe(teacher)}</p>
          {teacher.headline && (
            <p className="text-muted-foreground text-sm">{teacher.headline}</p>
          )}
          {teacher.profile?.school && (
            <p className="text-muted-foreground text-sm">
              {teacher.profile.school}
            </p>
          )}
          {teacher.profile?.about && (
            <p className="bg-muted/50 mt-2 rounded-md p-2.5 text-sm whitespace-pre-wrap">
              {teacher.profile.about}
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={result.waiting}
            onClick={() => decide({ userId: teacher.id, approve: true })}
          >
            <CheckIcon className="mr-1.5 size-4" />
            Approve
          </Button>
          {refusing ? (
            <>
              <Button
                size="sm"
                variant="destructive"
                disabled={result.waiting}
                onClick={() => decide({ userId: teacher.id, approve: false })}
              >
                Make them a student
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setRefusing(false)}
              >
                Cancel
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setRefusing(true)}
              aria-label={`Refuse ${teacher.name}`}
            >
              <XIcon className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </li>
  )
}

export const TeachersPanel = () => {
  const result = useAtomValue(teacherQueueAtom)
  const [decided, decide] = useAtom(decideTeacherAtom)

  if (Result.isFailure(result)) {
    return (
      <Card>
        <CardContent className="text-muted-foreground py-10 text-center text-sm">
          The teacher list could not be loaded.
        </CardContent>
      </Card>
    )
  }
  if (!Result.isSuccess(result)) {
    return <p className="text-muted-foreground p-6 text-sm">Loading…</p>
  }

  const { waiting, approved } = result.value

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <ClockIcon className="size-4" />
            Waiting for approval
            {waiting.length > 0 && (
              <Badge className="ml-1">{waiting.length}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {waiting.length === 0 ? (
            <p className="text-muted-foreground py-4 text-sm">
              Nobody is waiting. Teachers who sign up appear here before they
              can be put in front of a class.
            </p>
          ) : (
            <ul className="divide-y">
              {waiting.map((teacher) => (
                <Waiting key={teacher.id} teacher={teacher} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <GraduationCapIcon className="size-4" />
            Teaching ({approved.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {approved.length === 0 ? (
            <p className="text-muted-foreground py-4 text-sm">
              No approved teachers yet.
            </p>
          ) : (
            <ul className="divide-y">
              {approved.map((teacher) => (
                <li
                  key={teacher.id}
                  className="flex flex-wrap items-center gap-3 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{teacher.name}</p>
                    <p className="text-muted-foreground text-sm">
                      {describe(teacher)}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={decided.waiting}
                    onClick={() =>
                      decide({ userId: teacher.id, approve: false })
                    }
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
