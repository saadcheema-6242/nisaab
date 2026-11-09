import { createRootRoute, createRoute, redirect } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { Suspense, lazy } from 'react'
import { z } from 'zod'
import { AppShell } from '@/routes/_app-shell'

const LoadingPage = () => {
  return (
    <div className="flex h-screen items-center justify-center">Loading...</div>
  )
}

// Dynamic imports for code-splitting
const ProjectDetailRoute = lazy(() =>
  import('./project-detail-route').then((m) => ({
    default: m.ProjectDetailRoute,
  })),
)
const HomePage = lazy(() =>
  import('@/features/home/home-page').then((m) => ({ default: m.HomePage })),
)
const FeaturesPage = lazy(() =>
  import('@/features/marketing/features-page').then((m) => ({
    default: m.FeaturesPage,
  })),
)
const AboutPage = lazy(() =>
  import('@/features/marketing/about-page').then((m) => ({
    default: m.AboutPage,
  })),
)
const ContactPage = lazy(() =>
  import('@/features/marketing/contact-page').then((m) => ({
    default: m.ContactPage,
  })),
)
const VerifyEmailPage = lazy(() =>
  import('@/features/auth/verify-email-page').then((m) => ({
    default: m.VerifyEmailPage,
  })),
)
const SignInPage = lazy(() =>
  import('@/features/auth/sign-in-page').then((m) => ({
    default: m.SignInPage,
  })),
)
const SignUpPage = lazy(() =>
  import('@/features/auth/sign-up-page').then((m) => ({
    default: m.SignUpPage,
  })),
)
const ChatDetailRoute = lazy(() =>
  import('./chat-detail-route').then((m) => ({ default: m.ChatDetailRoute })),
)
const DocumentDetailRoute = lazy(() =>
  import('./document-detail-route').then((m) => ({
    default: m.DocumentDetailRoute,
  })),
)
const QuizDetailRoute = lazy(() =>
  import('./quiz-detail-route').then((m) => ({ default: m.QuizDetailRoute })),
)
const QuizEditRoute = lazy(() =>
  import('./quiz-edit-route').then((m) => ({ default: m.QuizEditRoute })),
)
const FlashcardDetailRoute = lazy(() =>
  import('./flashcard-detail-route').then((m) => ({
    default: m.FlashcardDetailRoute,
  })),
)
const FlashcardEditRoute = lazy(() =>
  import('./flashcard-edit-route').then((m) => ({
    default: m.FlashcardEditRoute,
  })),
)
const NoteDetailRoute = lazy(() =>
  import('./note-detail-route').then((m) => ({
    default: m.NoteDetailRoute,
  })),
)
const MindMapDetailRoute = lazy(() =>
  import('./mind-map-detail-route').then((m) => ({
    default: m.MindMapDetailRoute,
  })),
)

const AdminPage = lazy(() =>
  import('@/features/admin/admin-page').then((m) => ({
    default: m.AdminPage,
  })),
)
const CommunityPage = lazy(() =>
  import('@/features/community/community-page').then((m) => ({
    default: m.CommunityPage,
  })),
)
const ProgressPage = lazy(() =>
  import('@/features/progress/progress-page').then((m) => ({
    default: m.ProgressPage,
  })),
)
const AwaitingApprovalPage = lazy(() =>
  import('@/features/onboarding/awaiting-approval-page').then((m) => ({
    default: m.AwaitingApprovalPage,
  })),
)
const SessionsPage = lazy(() =>
  import('@/features/sessions/sessions-page').then((m) => ({
    default: m.SessionsPage,
  })),
)
const ReviewPage = lazy(() =>
  import('@/features/review/review-page').then((m) => ({
    default: m.ReviewPage,
  })),
)
const PaperRoute = lazy(() =>
  import('./paper-route').then((m) => ({ default: m.PaperRoute })),
)
const SrqRoute = lazy(() =>
  import('./srq-route').then((m) => ({ default: m.SrqRoute })),
)

const StudyPlanRoute = lazy(() =>
  import('./study-plan-route').then((m) => ({
    default: m.StudyPlanRoute,
  })),
)
const SettingsPage = lazy(() =>
  import('@/features/settings/settings-page').then((m) => ({
    default: m.SettingsPage,
  })),
)
const DashboardRoute = lazy(() =>
  import('./dashboard-route').then((m) => ({ default: m.DashboardRoute })),
)
const OnboardingPage = lazy(() =>
  import('@/features/onboarding/onboarding-page').then((m) => ({
    default: m.OnboardingPage,
  })),
)
// Decides between the student page and the teacher page once the server
// has said which this account is. See features/dashboard/dashboard-home.
// Opened by people with no account, so it is deliberately outside the
// dashboard tree and its guards. See features/share/shared-page.
const SharedPage = lazy(() =>
  import('@/features/share/shared-page').then((m) => ({
    default: m.SharedPage,
  })),
)
const HistoryPage = lazy(() =>
  import('@/features/history/history-page').then((m) => ({
    default: m.HistoryPage,
  })),
)
const LibraryPage = lazy(() =>
  import('@/features/history/library-page').then((m) => ({
    default: m.LibraryPage,
  })),
)
const DashboardHome = lazy(() =>
  import('@/features/dashboard/dashboard-home').then((m) => ({
    default: m.DashboardHome,
  })),
)

const requireAuth = async () => {
  // Check if user is signed in (waits for the saved session to be restored)
  const { getCurrentUser } = await import('@/lib/auth-client')
  const user = await getCurrentUser()

  if (!user) {
    const isSignInPage = window.location.pathname === '/sign-in'

    throw redirect({
      to: '/sign-in',
      search: {
        redirect: isSignInPage ? undefined : window.location.pathname,
      },
    })
  }

  // Signed in is not the same as confirmed. The API refuses a new account
  // whose address has never been confirmed, so letting one through to the
  // dashboard produces a page where every panel fails and nothing says why:
  // the student sees "Failed to load your subjects" and has no idea an email
  // is waiting for them. Checked here because this is the one place both
  // /dashboard and /onboarding pass through.
  //
  // Google accounts arrive verified and never see this.
  if (!user.emailVerified) {
    throw redirect({ to: '/verify-email' })
  }
}

export const rootRoute = createRootRoute({
  component: () => (
    <>
      <AppShell />
      <TanStackRouterDevtools />
    </>
  ),
})

// Dashboard layout route - parent for all authenticated routes
export const dashboardRoute = createRoute({
  path: '/dashboard',
  getParentRoute: () => rootRoute,
  beforeLoad: requireAuth,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <DashboardRoute />
    </Suspense>
  ),
})

export const indexRoute = createRoute({
  path: '/',
  getParentRoute: () => rootRoute,
  validateSearch: z.object({ redirect: z.string().optional() }).optional(),
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <HomePage />
    </Suspense>
  ),
})

// The public site. Open to everyone; a signed-in student is sent to /dashboard.
export const featuresRoute = createRoute({
  path: '/features',
  getParentRoute: () => rootRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <FeaturesPage />
    </Suspense>
  ),
})

export const aboutRoute = createRoute({
  path: '/about',
  getParentRoute: () => rootRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <AboutPage />
    </Suspense>
  ),
})

export const contactRoute = createRoute({
  path: '/contact',
  getParentRoute: () => rootRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <ContactPage />
    </Suspense>
  ),
})

export const awaitingApprovalRoute = createRoute({
  path: '/awaiting-approval',
  getParentRoute: () => rootRoute,
  beforeLoad: requireAuth,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <AwaitingApprovalPage />
    </Suspense>
  ),
})

export const onboardingRoute = createRoute({
  path: '/onboarding',
  getParentRoute: () => rootRoute,
  beforeLoad: requireAuth,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <OnboardingPage />
    </Suspense>
  ),
})

export const verifyEmailRoute = createRoute({
  path: '/verify-email',
  getParentRoute: () => rootRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <VerifyEmailPage />
    </Suspense>
  ),
})

export const signInRoute = createRoute({
  path: '/sign-in',
  getParentRoute: () => rootRoute,
  validateSearch: z.object({ redirect: z.string().optional() }).optional(),
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <SignInPage />
    </Suspense>
  ),
})

export const signUpRoute = createRoute({
  path: '/sign-up',
  getParentRoute: () => rootRoute,
  validateSearch: z.object({ redirect: z.string().optional() }).optional(),
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <SignUpPage />
    </Suspense>
  ),
})

/**
 * A shared quiz or paper. No sign-in, no app shell, no guards.
 *
 * A child of the root rather than of the dashboard, because everything
 * under the dashboard asks who you are and this page's whole point is
 * that it does not.
 */
export const sharedRoute = createRoute({
  path: '/s/$token',
  getParentRoute: () => rootRoute,
  component: function Shared() {
    const { token } = sharedRoute.useParams()
    return (
      <Suspense fallback={<LoadingPage />}>
        <SharedPage token={token} />
      </Suspense>
    )
  },
})

export const historyRoute = createRoute({
  path: '/history',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <HistoryPage />
    </Suspense>
  ),
})

export const libraryRoute = createRoute({
  path: '/library',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <LibraryPage />
    </Suspense>
  ),
})

export const dashboardIndexRoute = createRoute({
  path: '/',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <DashboardHome />
    </Suspense>
  ),
})

export const projectDetailRoute = createRoute({
  path: '/p/$projectId',
  getParentRoute: () => dashboardRoute,
  // slo: open the syllabus map with this SLO's panel (e.g. from the dashboard)
  validateSearch: z.object({ slo: z.string().optional() }).optional(),
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <ProjectDetailRoute />
    </Suspense>
  ),
})

export const chatDetailRoute = createRoute({
  path: '/p/$projectId/c/$chatId',
  getParentRoute: () => dashboardRoute,
  // ask: a first message to send automatically (e.g. from the syllabus map)
  validateSearch: z.object({ ask: z.string().optional() }).optional(),
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <ChatDetailRoute />
    </Suspense>
  ),
})

export const documentDetailRoute = createRoute({
  path: '/p/$projectId/d/$documentId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <DocumentDetailRoute />
    </Suspense>
  ),
})

export const flashcardDetailRoute = createRoute({
  path: '/p/$projectId/f/$flashcardGroupId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <FlashcardDetailRoute />
    </Suspense>
  ),
})

export const flashcardEditRoute = createRoute({
  path: '/p/$projectId/f/$flashcardGroupId/edit',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <FlashcardEditRoute />
    </Suspense>
  ),
})

export const quizDetailRoute = createRoute({
  path: '/p/$projectId/q/$quizId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <QuizDetailRoute />
    </Suspense>
  ),
})

export const quizEditRoute = createRoute({
  path: '/p/$projectId/q/$quizId/edit',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <QuizEditRoute />
    </Suspense>
  ),
})

export const noteDetailRoute = createRoute({
  path: '/p/$projectId/n/$noteId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <NoteDetailRoute />
    </Suspense>
  ),
})

export const mindMapDetailRoute = createRoute({
  path: '/p/$projectId/m/$mindMapId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <MindMapDetailRoute />
    </Suspense>
  ),
})

export const adminRoute = createRoute({
  path: '/admin',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <AdminPage />
    </Suspense>
  ),
})

export const communityRoute = createRoute({
  path: '/community',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <CommunityPage />
    </Suspense>
  ),
})

export const sessionsRoute = createRoute({
  path: '/sessions',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <SessionsPage />
    </Suspense>
  ),
})

export const progressRoute = createRoute({
  path: '/progress',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <ProgressPage />
    </Suspense>
  ),
})

export const reviewRoute = createRoute({
  path: '/review',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <ReviewPage />
    </Suspense>
  ),
})

export const paperRoute = createRoute({
  path: '/p/$projectId/paper/$paperId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <PaperRoute />
    </Suspense>
  ),
})

export const srqRoute = createRoute({
  path: '/p/$projectId/srq/$questionId',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <SrqRoute />
    </Suspense>
  ),
})

export const studyPlanRoute = createRoute({
  path: '/p/$projectId/study-plan',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <StudyPlanRoute />
    </Suspense>
  ),
})

export const settingsRoute = createRoute({
  path: '/settings',
  getParentRoute: () => dashboardRoute,
  component: () => (
    <Suspense fallback={<LoadingPage />}>
      <SettingsPage />
    </Suspense>
  ),
})

export const routeTree = rootRoute.addChildren([
  dashboardRoute.addChildren([
    dashboardIndexRoute,
    projectDetailRoute,
    chatDetailRoute,
    documentDetailRoute,
    flashcardDetailRoute,
    flashcardEditRoute,
    quizDetailRoute,
    quizEditRoute,
    noteDetailRoute,
    mindMapDetailRoute,
    srqRoute,
    paperRoute,
    reviewRoute,
    communityRoute,
    adminRoute,
    progressRoute,
    sessionsRoute,
    historyRoute,
    libraryRoute,

    studyPlanRoute,
    settingsRoute,
  ]),
  sharedRoute,
  indexRoute,
  featuresRoute,
  aboutRoute,
  contactRoute,
  onboardingRoute,
  awaitingApprovalRoute,
  signInRoute,
  signUpRoute,
  verifyEmailRoute,
])
