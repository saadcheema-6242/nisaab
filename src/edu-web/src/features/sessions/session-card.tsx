/**
 * One class on a timetable.
 *
 * The join button is governed by the server, not by this component. The
 * link simply is not in the response until the session opens, so there is
 * nothing here to hide and nothing to find in the network tab. What this
 * decides is only what to say in its place.
 */

import { CalendarClockIcon, UserRoundIcon, VideoIcon } from 'lucide-react'
import type { StudentSession } from '@/data-acess/sessions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { SubjectIcon } from '@/lib/subjects'
import { cn } from '@/lib/utils'

const GROUP_NAMES: Record<string, string> = {
  PRE_MED: 'Pre-Medical',
  PRE_ENG: 'Pre-Engineering',
  ICS: 'ICS',
}

export const SessionCard = ({
  session,
  groups,
  children,
}: {
  session: StudentSession
  /** Shown to teachers and admins, so they can see who the class serves. */
  groups?: Array<string>
  children?: React.ReactNode
}) => {
  const open = session.state === 'open'

  return (
    <Card className={cn(open && 'border-primary')}>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start gap-3">
          <SubjectIcon code={session.subject_code} className="mt-0.5 size-5 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-medium">{session.title}</h3>
              {open && (
                <Badge className="bg-emerald-600 hover:bg-emerald-600">
                  Happening now
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground text-sm">
              {session.subject_name} · Class {session.grade}
            </p>
          </div>
        </div>

        {session.description && (
          <p className="text-sm whitespace-pre-wrap">{session.description}</p>
        )}

        {session.teacher && (
          <div className="flex items-start gap-2 text-sm">
            <UserRoundIcon className="text-muted-foreground mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">{session.teacher.name}</p>
              {session.teacher.headline && (
                <p className="text-muted-foreground text-xs">
                  {session.teacher.headline}
                </p>
              )}
            </div>
          </div>
        )}

        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <CalendarClockIcon className="size-4 shrink-0" />
          <span>
            {session.when} · {session.duration_minutes} minutes
          </span>
        </div>

        {groups && groups.length > 0 && (
          <p className="text-muted-foreground text-xs">
            Open to {groups.map((g) => GROUP_NAMES[g] ?? g).join(', ')}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {session.join_url ? (
            <Button asChild size="sm">
              {/* noreferrer as well as noopener: the meeting host has no
                  business being told which page the student came from. */}
              <a
                href={session.join_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <VideoIcon className="mr-1.5 size-4" />
                Join now
              </a>
            </Button>
          ) : (
            <p className="text-muted-foreground text-xs">
              The join button appears fifteen minutes before it starts.
            </p>
          )}
          {children}
        </div>
      </CardContent>
    </Card>
  )
}
