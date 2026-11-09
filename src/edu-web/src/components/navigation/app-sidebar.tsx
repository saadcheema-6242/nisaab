import {
  BarChart3Icon,
  CalendarDaysIcon,
  ClipboardCheckIcon,
  GraduationCapIcon,
  LayoutDashboardIcon,
  MessageSquareIcon,
  Settings2,
  ShieldIcon,
} from 'lucide-react'
import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { NavMain } from './nav-main'
import { NavProjects } from './nav-projects'
import { NavUser } from './nav-user'
import { NisaabMark } from '@/components/nisaab-mark'
import { brand } from '@/lib/brand'
import { adminStateAtom } from '@/data-acess/admin'
import { reviewerStateAtom } from '@/data-acess/review'
import { accountStateAtom } from '@/data-acess/teachers'
import { surfaceFor } from '@/lib/surface'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const adminResult = useAtomValue(adminStateAtom)
  const isAdmin = Result.isSuccess(adminResult) && adminResult.value.is_admin
  const reviewerResult = useAtomValue(reviewerStateAtom)
  const isReviewer =
    Result.isSuccess(reviewerResult) && reviewerResult.value.is_reviewer

  // A teacher has no cohort, so the student pages have nothing to read.
  // The same rule guards the routes themselves; see lib/surface.
  const accountResult = useAtomValue(accountStateAtom)
  const surface = Result.isSuccess(accountResult)
    ? surfaceFor(accountResult.value)
    : 'student'
  const teaching = surface === 'teacher'

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              asChild
            >
              <Link to="/dashboard">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <NisaabMark className="size-5" />
                </div>
                <span className="text-lg font-bold">{brand.name}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {!teaching && <NavProjects />}
        <NavMain
          items={[
            // A teacher's dashboard is their classes, so the home link is
            // named for that rather than for a syllabus they do not study.
            {
              title: teaching ? 'My classes' : 'My FSc',
              url: '/dashboard',
              icon: teaching ? GraduationCapIcon : LayoutDashboardIcon,
            },
            {
              title: 'Sessions',
              url: '/dashboard/sessions',
              icon: CalendarDaysIcon,
            },
            // Progress and the class rooms both read a StudentProfile a
            // teacher does not have.
            ...(teaching
              ? []
              : [
                  {
                    title: 'Progress',
                    url: '/dashboard/progress',
                    icon: BarChart3Icon,
                  },
                  {
                    title: 'Community',
                    url: '/dashboard/community',
                    icon: MessageSquareIcon,
                  },
                ]),
            ...(isAdmin
              ? [
                  {
                    title: 'Accounts',
                    url: '/dashboard/admin',
                    icon: ShieldIcon,
                  },
                ]
              : []),
            ...(isReviewer
              ? [
                  {
                    title: 'Review content',
                    url: '/dashboard/review',
                    icon: ClipboardCheckIcon,
                  },
                ]
              : []),
            {
              title: 'Settings',
              url: '/dashboard/settings',
              icon: Settings2,
            },
          ]}
        />
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
