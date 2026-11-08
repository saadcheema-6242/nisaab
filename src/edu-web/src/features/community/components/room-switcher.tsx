/**
 * Which room an administrator is looking at.
 *
 * Shown to nobody else, and it is not what keeps students out: the server
 * ignores the request entirely unless the caller is on the admin list, and
 * reads an ordinary student's room from their profile. This only changes
 * what an administrator asks for.
 *
 * An administrator belongs to no cohort, so leaving them pinned to whichever
 * group they happened to pick at onboarding would show them one of six rooms
 * and hide the rest, with nothing on screen to say so.
 */

import { Result, useAtom, useAtomValue } from '@effect-atom/atom-react'
import { UsersIcon } from 'lucide-react'
import { viewingRoomAtom } from '@/data-acess/community'
import { accountStateAtom } from '@/data-acess/teachers'
import { cn } from '@/lib/utils'

const ROOMS = [
  { grade: 11, group_code: 'PRE_MED', label: 'Pre-Medical XI' },
  { grade: 11, group_code: 'PRE_ENG', label: 'Pre-Engineering XI' },
  { grade: 11, group_code: 'ICS', label: 'ICS XI' },
  { grade: 12, group_code: 'PRE_MED', label: 'Pre-Medical XII' },
  { grade: 12, group_code: 'PRE_ENG', label: 'Pre-Engineering XII' },
  { grade: 12, group_code: 'ICS', label: 'ICS XII' },
]

export const RoomSwitcher = () => {
  const account = useAtomValue(accountStateAtom)
  const [viewing, setViewing] = useAtom(viewingRoomAtom)

  if (!Result.isSuccess(account) || !account.value.is_admin) return null

  return (
    <div className="space-y-2">
      <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
        <UsersIcon className="size-3.5" />
        You are an administrator, so you can read any room.
      </p>
      <div className="flex flex-wrap gap-1.5">
        {ROOMS.map((room) => {
          const here =
            viewing?.grade === room.grade &&
            viewing.group_code === room.group_code
          return (
            <button
              key={room.label}
              type="button"
              aria-pressed={here}
              onClick={() =>
                setViewing({ grade: room.grade, group_code: room.group_code })
              }
              className={cn(
                'rounded-full border px-3 py-1 text-xs transition-colors',
                here
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'hover:bg-muted',
              )}
            >
              {room.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
