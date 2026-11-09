import { describe, expect, it } from 'vitest'
import { surfaceFor, teacherMayOpen } from './surface'

/**
 * Which surface an account gets, and what a teacher may open.
 *
 * Worth testing because it is enforced in two places - the sidebar offers
 * links, the route guard allows pages - and the two disagreeing is how a
 * teacher ends up either staring at a page built for a cohort they do not
 * have, or clicking a link that bounces them. The rule is one function so
 * that it can be checked once, here.
 */

const account = (over: Partial<Parameters<typeof surfaceFor>[0]> = {}) => ({
  role: 'student' as const,
  is_admin: false,
  teacher_approved: false,
  ...over,
})

describe('surfaceFor', () => {
  it('an ordinary account is a student', () => {
    expect(surfaceFor(account())).toBe('student')
  })

  it('an approved teacher is a teacher', () => {
    expect(
      surfaceFor(account({ role: 'teacher', teacher_approved: true })),
    ).toBe('teacher')
  })

  it('a teacher who has only applied is not one yet', () => {
    // The guard holds them on the waiting page, so in practice they never
    // reach a surface at all. If that ever stops being true, they must
    // fall back to the student pages rather than be handed the teacher's.
    expect(
      surfaceFor(account({ role: 'teacher', teacher_approved: false })),
    ).toBe('student')
  })

  it('an administrator outranks both, approved or not', () => {
    expect(surfaceFor(account({ is_admin: true }))).toBe('admin')
    expect(
      surfaceFor(
        account({ role: 'teacher', teacher_approved: true, is_admin: true }),
      ),
    ).toBe('admin')
    // Deliberately: an administrator is a student of every cohort, so
    // never narrowed to the teacher surface.
    expect(
      surfaceFor(
        account({ role: 'teacher', teacher_approved: false, is_admin: true }),
      ),
    ).toBe('admin')
  })
})

describe('teacherMayOpen', () => {
  it('allows their own pages', () => {
    expect(teacherMayOpen('/dashboard')).toBe(true)
    expect(teacherMayOpen('/dashboard/sessions')).toBe(true)
    expect(teacherMayOpen('/dashboard/settings')).toBe(true)
  })

  it('refuses the pages that read a student profile', () => {
    expect(teacherMayOpen('/dashboard/community')).toBe(false)
    expect(teacherMayOpen('/dashboard/progress')).toBe(false)
    expect(teacherMayOpen('/dashboard/review')).toBe(false)
    expect(teacherMayOpen('/dashboard/admin')).toBe(false)
  })

  it('refuses a project, whatever its id', () => {
    expect(teacherMayOpen('/dashboard/p/abc123')).toBe(false)
    expect(teacherMayOpen('/dashboard/p/abc123/c/chat1')).toBe(false)
  })

  it('is not fooled by a trailing slash', () => {
    // The router can hand either form over, and a path that slips through
    // on a slash is a hole rather than a cosmetic bug.
    expect(teacherMayOpen('/dashboard/')).toBe(true)
    expect(teacherMayOpen('/dashboard/sessions/')).toBe(true)
    expect(teacherMayOpen('/dashboard/community/')).toBe(false)
  })
})
