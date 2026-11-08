/**
 * Looking after the accounts.
 *
 * Three powers, in increasing order of how sorry you will be if you get one
 * wrong: look, suspend, delete. The screen is laid out in that order, and the
 * dangerous one is behind a typed confirmation rather than a button that sits
 * next to the others waiting to be clicked by accident.
 *
 * The page is only reachable by an administrator, but that is enforced on the
 * server. This hides the controls; it does not protect anything.
 */

import { useState } from 'react'
import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { ShieldIcon, Trash2Icon } from 'lucide-react'
import { ModerationPanel } from './moderation-panel'
import { SessionsPanel } from './sessions-panel'
import type { AdminUser } from '@/data-acess/admin'
import {
  adminUsersAtom,
  banUserAtom,
  deleteAllUsersAtom,
  deleteUserAtom,
  unbanUserAtom,
} from '@/data-acess/admin'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { auth } from '@/lib/auth-client'
import { cn } from '@/lib/utils'

/** Who this browser is signed in as, for the refusal message. */
const currentEmail = () => auth.currentUser?.email ?? null

const GROUPS: Record<string, string> = {
  PRE_MED: 'Pre-Medical',
  PRE_ENG: 'Pre-Engineering',
  ICS: 'ICS',
}

const day = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric',
  }) : ''

const Stat = ({ label, value }: { label: string; value: number }) => (
  <div className="rounded-lg border p-3">
    <div className="text-2xl font-semibold tabular-nums">{value}</div>
    <div className="text-xs text-muted-foreground">{label}</div>
  </div>
)

/** Everything that can be done to one account, kept together. */
const Actions = ({ user }: { user: AdminUser }) => {
  const [reason, setReason] = useState('')
  const [days, setDays] = useState<number | null>(7)
  const [confirmEmail, setConfirmEmail] = useState('')
  const [deleting, setDeleting] = useState(false)
  const ban = useAtomSet(banUserAtom)
  const unban = useAtomSet(unbanUserAtom)
  const remove = useAtomSet(deleteUserAtom)

  const suspended = user.ban_state !== 'active'
  const emailMatches =
    confirmEmail.trim().toLowerCase() === (user.email ?? '').trim().toLowerCase()

  return (
    <div className="space-y-3 border-t pt-3">
      {suspended ? (
        <div className="space-y-2">
          <p className="text-sm">
            <span className="font-medium">
              {user.ban_state === 'permanent'
                ? 'Suspended indefinitely'
                : `Suspended until ${day(user.banned_until)}`}
            </span>
            {user.ban_reason && (
              <span className="text-muted-foreground"> · {user.ban_reason}</span>
            )}
            {user.banned_by && (
              <span className="text-muted-foreground"> · by {user.banned_by}</span>
            )}
          </p>
          <Button size="sm" variant="outline" onClick={() => unban(user.id)}>
            Lift suspension
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {[1, 7, 30].map((n) => (
              <Button
                key={n}
                size="sm"
                variant={days === n ? 'default' : 'outline'}
                onClick={() => setDays(n)}
              >
                {n} {n === 1 ? 'day' : 'days'}
              </Button>
            ))}
            <Button
              size="sm"
              variant={days === null ? 'destructive' : 'outline'}
              onClick={() => setDays(null)}
            >
              Permanent
            </Button>
          </div>
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (the student is shown this)"
          />
          <Button
            size="sm"
            variant="secondary"
            disabled={!reason.trim()}
            onClick={() => {
              ban({ userId: user.id, days, reason: reason.trim() })
              setReason('')
            }}
          >
            Suspend
          </Button>
        </div>
      )}

      {/* Deleting is kept apart from everything else, because it is the only
          action here that cannot be undone. */}
      {deleting ? (
        <div className="space-y-2 rounded-lg border border-destructive/40 bg-destructive/5 p-3">
          <p className="text-sm font-medium text-destructive">
            This removes the account and everything in it. There is no undo.
          </p>
          <p className="text-xs text-muted-foreground">
            Type <span className="font-mono">{user.email}</span> to confirm.
          </p>
          <Input
            value={confirmEmail}
            onChange={(e) => setConfirmEmail(e.target.value)}
            placeholder="Type the email address"
            autoComplete="off"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              disabled={!emailMatches}
              onClick={() =>
                remove({ userId: user.id, confirmEmail: confirmEmail.trim() })
              }
            >
              Delete permanently
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setDeleting(false)
                setConfirmEmail('')
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setDeleting(true)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive"
        >
          <Trash2Icon className="size-3.5" />
          Delete this account
        </button>
      )}
    </div>
  )
}

const UserRow = ({ user }: { user: AdminUser }) => {
  const [open, setOpen] = useState(false)
  const used =
    user.usage.chat_messages +
    user.usage.quiz_generations +
    user.usage.flashcard_generations +
    user.usage.mindmap_generations +
    user.usage.document_uploads

  return (
    <Card className={cn(user.ban_state !== 'active' && 'border-destructive/40')}>
      <CardContent className="space-y-2 pt-4">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="w-full text-left"
        >
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="font-medium">{user.name || 'No name'}</span>
            <span className="text-sm text-muted-foreground">{user.email}</span>
            {user.ban_state === 'permanent' && (
              <Badge variant="destructive">Banned</Badge>
            )}
            {user.ban_state === 'temporary' && (
              <Badge variant="destructive">
                Suspended to {day(user.banned_until)}
              </Badge>
            )}
            {!user.onboarded && <Badge variant="outline">Not onboarded</Badge>}
          </div>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
            {user.group_code && (
              <span>
                {GROUPS[user.group_code] ?? user.group_code}
                {user.grade ? ` ${user.grade === 11 ? 'XI' : 'XII'}` : ''}
              </span>
            )}
            {user.language && <span>{user.language}</span>}
            <span>{user.practice_answers} answers</span>
            <span>{used} actions today</span>
            <span>joined {day(user.created_at)}</span>
          </div>
        </button>

        {open && (
          <>
            <div className="grid grid-cols-2 gap-2 pt-1 text-xs sm:grid-cols-5">
              <Stat label="Chat today" value={user.usage.chat_messages} />
              <Stat label="Quizzes today" value={user.usage.quiz_generations} />
              <Stat label="Cards today" value={user.usage.flashcard_generations} />
              <Stat label="Maps today" value={user.usage.mindmap_generations} />
              <Stat label="Uploads today" value={user.usage.document_uploads} />
            </div>
            <Actions user={user} />
          </>
        )}
      </CardContent>
    </Card>
  )
}


const WIPE_PHRASE = 'DELETE ALL USERS'

/**
 * Wiping the system.
 *
 * Kept at the bottom, behind a disclosure, and needing a typed phrase. The
 * count is shown and sent: if the page is stale, or this is not the system
 * the administrator thinks they are looking at, the server refuses rather
 * than deleting the wrong database.
 */
const WipeEverything = ({ others }: { others: number }) => {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const wipe = useAtomSet(deleteAllUsersAtom)
  const ready = typed === WIPE_PHRASE && others > 0

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-muted-foreground hover:text-destructive"
      >
        Delete all accounts…
      </button>
    )
  }

  return (
    <Card className="border-destructive/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-base text-destructive">
          Delete all accounts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">
          This permanently deletes{' '}
          <span className="font-semibold">{others} accounts</span> and
          everything in them: projects, chats, documents, quizzes, papers,
          answers and progress. Your own account is kept. There is no undo.
        </p>
        <p className="text-xs text-muted-foreground">
          Take a database backup first. Type{' '}
          <span className="font-mono font-semibold">{WIPE_PHRASE}</span> to
          confirm.
        </p>
        <Input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder={WIPE_PHRASE}
          autoComplete="off"
        />
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="destructive"
            disabled={!ready}
            onClick={() => {
              wipe({ confirm: typed, expectedCount: others })
              setTyped('')
              setOpen(false)
            }}
          >
            Delete {others} accounts
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setOpen(false)
              setTyped('')
            }}
          >
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export const AdminPage = () => {
  const [search, setSearch] = useState('')
  const result = useAtomValue(adminUsersAtom)

  // Three states, not two. Waiting and refused look identical if you only ask
  // "did it succeed", and a refusal that renders as "Loading..." forever is
  // the same bug as one that renders as a blank screen.
  if (Result.isFailure(result)) {
    return (
      <div className="mx-auto w-full max-w-xl p-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Not available</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              This account cannot manage other accounts. Administrators are
              listed in ADMIN_EMAILS on the server, and the address must match
              the one you are signed in with.
            </p>
            <p>
              Signed in as{' '}
              <span className="font-medium text-foreground">
                {currentEmail() ?? 'an unknown account'}
              </span>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!Result.isSuccess(result)) {
    return <div className="p-6 text-sm text-muted-foreground">Loading accounts…</div>
  }

  const { overview, users } = result.value
  const wanted = search.trim().toLowerCase()
  const shown = wanted
    ? users.filter(
        (u) =>
          (u.email ?? '').toLowerCase().includes(wanted) ||
          (u.name ?? '').toLowerCase().includes(wanted),
      )
    : users

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <ShieldIcon className="size-6" />
          Accounts
        </h1>
        <p className="text-sm text-muted-foreground">
          Counts, not contents. Reading a student's own work is a different
          decision and is not what this screen is for.
        </p>
      </header>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Across the system</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Stat label="Accounts" value={overview.total_users} />
          <Stat label="Onboarded" value={overview.onboarded_users} />
          <Stat label="Active today" value={overview.active_today} />
          <Stat label="Suspended" value={overview.banned_users} />
          <Stat label="Answers recorded" value={overview.practice_answers} />
        </CardContent>
        {Object.keys(overview.by_group).length > 0 && (
          <CardContent className="flex flex-wrap gap-2 pt-0 text-xs text-muted-foreground">
            {Object.entries(overview.by_group).map(([code, n]) => (
              <span key={code} className="rounded-full border px-2.5 py-1">
                {GROUPS[code] ?? code}: {n}
              </span>
            ))}
            {Object.entries(overview.by_grade).map(([grade, n]) => (
              <span key={grade} className="rounded-full border px-2.5 py-1">
                Class {grade === '11' ? 'XI' : 'XII'}: {n}
              </span>
            ))}
          </CardContent>
        )}
      </Card>

      <ModerationPanel />

      <SessionsPanel />

      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name or email…"
      />

      {shown.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No accounts match that.
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-2">
          {shown.map((user) => (
            <li key={user.id}>
              <UserRow user={user} />
            </li>
          ))}
        </ul>
      )}

      <div className="pt-6">
        <WipeEverything others={Math.max(0, overview.total_users - 1)} />
      </div>
    </div>
  )
}

export default AdminPage
