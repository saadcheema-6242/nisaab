import { RegistryProvider } from '@effect-atom/atom-react'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'

import { routeTree } from './routes/_config.tsx'

import * as TanStackQueryProvider from './integrations/tanstack-query/root-provider.tsx'

import { Toaster } from './components/ui/sonner.tsx'
import reportWebVitals from './reportWebVitals.ts'
import { TooltipProvider } from '@/components/ui/tooltip.tsx'
import { ModalProvider } from '@/providers/modal-provider.tsx'
import { ThemeProvider } from '@/providers/theme-provider.tsx'
import 'katex/dist/katex.min.css'
// Registers \ce{} for chemical formulas in KaTeX
import 'katex/contrib/mhchem'
import './styles.css'

const TanStackQueryProviderContext = TanStackQueryProvider.getContext()
const router = createRouter({
  routeTree: routeTree,
  context: {
    ...TanStackQueryProviderContext,
  },
  defaultPreload: 'intent',
  scrollRestoration: true,
  defaultStructuralSharing: true,
  defaultPreloadStaleTime: 0,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const rootElement = document.getElementById('app')
if (rootElement && !rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <StrictMode>
      <ThemeProvider>
        <RegistryProvider>
          <TanStackQueryProvider.Provider {...TanStackQueryProviderContext}>
            <TooltipProvider>
              <ModalProvider>
                <Toaster richColors />
                <RouterProvider router={router} />
              </ModalProvider>
            </TooltipProvider>
          </TanStackQueryProvider.Provider>
        </RegistryProvider>
      </ThemeProvider>
    </StrictMode>,
  )
}

/**
 * Catch the install prompt before anything can ask for it.
 *
 * Chrome fires `beforeinstallprompt` within a second or two of load and
 * will not fire it again. The settings page, where the Install button
 * lives, is opened minutes later, so a listener there would always miss
 * it. Parked on `window` and read by features/settings/install-app.
 *
 * preventDefault stops Chrome's own mini-infobar, which otherwise
 * appears over the page uninvited; the student presses our button
 * instead, or follows the written steps.
 */
window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault()
  window.__nisaabInstallPrompt = event as typeof window.__nisaabInstallPrompt
})

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals()
