import { ClipboardCheckIcon, LayoutDashboardIcon, Settings2 } from 'lucide-react'
import { NisaabMark } from '@/components/nisaab-mark'
import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { NavMain } from './nav-main'
import { NavProjects } from './nav-projects'
import { NavUser } from './nav-user'
import { brand } from '@/lib/brand'
import { reviewerStateAtom } from '@/data-acess/review'
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
  const reviewerResult = useAtomValue(reviewerStateAtom)
  const isReviewer =
    Result.isSuccess(reviewerResult) && reviewerResult.value.is_reviewer

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
        <NavProjects />
        <NavMain
          items={[
            {
              title: 'My FSc',
              url: '/dashboard',
              icon: LayoutDashboardIcon,
            },
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
