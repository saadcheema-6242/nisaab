/**
 * Which parts of the app an account is for.
 *
 * A teacher is not a student with a different badge. They have no
 * StudentProfile, no cohort, no subjects and no syllabus, so "My FSc",
 * Progress, the project list and the class rooms are not merely empty for
 * them - they are unanswerable. Every one of those pages reads a profile
 * that does not exist and either shows nothing or explains itself in terms
 * of subjects the teacher does not study.
 *
 * The rule lives here, once, because it has to be obeyed in two places
 * that would otherwise drift: the sidebar decides what to offer, and the
 * route guard decides what to allow. A sidebar that hides a link is not
 * access control - the URL still works - and a guard that blocks a page
 * the sidebar still shows is a dead end the user is invited to walk into.
 *
 * An administrator is deliberately all three: a student of every cohort, a
 * teacher, and the person who approves teachers. They see everything.
 */

export type Surface = 'student' | 'teacher' | 'admin'

export const surfaceFor = (account: {
  role: 'student' | 'teacher'
  is_admin: boolean
  teacher_approved: boolean
}): Surface => {
  if (account.is_admin) return 'admin'
  // An unapproved teacher never gets this far - the guard holds them on
  // the waiting page - but if they did, they are not a teacher yet.
  if (account.role === 'teacher' && account.teacher_approved) return 'teacher'
  return 'student'
}

/**
 * The dashboard paths a teacher may open. Everything else belongs to the
 * student surface and sends them back to their own dashboard.
 *
 * Settings is on the list because it is where signing out lives, and
 * sessions because it is the whole job.
 */
const TEACHER_PATHS = [
  '/dashboard',
  '/dashboard/sessions',
  '/dashboard/settings',
  // Not History or Library: both read a student's own projects, which a
  // teacher does not have, so they would be permanently empty.
]

export const teacherMayOpen = (pathname: string): boolean => {
  const path = pathname.replace(/\/+$/, '') || '/dashboard'
  return TEACHER_PATHS.includes(path)
}
