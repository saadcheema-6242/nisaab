/**
 * Installing NISAAB as an app, on whatever the student is holding.
 *
 * NISAAB is a web app, which is the right choice for students who share
 * a phone and have little storage: there is nothing to download from a
 * store and nothing to update. Installed, it still gets an icon on the
 * home screen or in the dock, and opens without the browser's address
 * bar and tabs around it.
 *
 * Two routes, because browsers disagree:
 *
 *   Chrome, Edge and the Android browsers fire `beforeinstallprompt`,
 *   which can be held and replayed when the student presses a button.
 *   That is the one-tap path, and it is offered when it exists.
 *
 *   Safari fires nothing, ever. On an iPhone the only way in is Share,
 *   then Add to Home Screen, and no amount of JavaScript changes that.
 *
 * So the written steps are always shown rather than hidden behind a
 * failed feature check: a button that never appears, on a page that then
 * says nothing, is worse than instructions that always work. The
 * student's own platform is opened first and the rest are collapsed.
 *
 * The event can also fire before this component mounts, which is most
 * of the time - it is a settings page, reached minutes after load. The
 * listener in main.tsx catches it and parks it on `window`, and this
 * reads from there.
 */

import { useEffect, useState } from 'react'
import {
  AppleIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  DownloadIcon,
  MonitorIcon,
  SmartphoneIcon,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { brand } from '@/lib/brand'
import { cn } from '@/lib/utils'

/** The event Chrome fires, which the standard DOM types do not name. */
type InstallPrompt = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

declare global {
  interface Window {
    __nisaabInstallPrompt?: InstallPrompt
  }
}

type Platform = 'android' | 'ios' | 'windows' | 'macos' | 'linux'

const GUIDES: Array<{
  id: Platform
  label: string
  icon: React.ComponentType<{ className?: string }>
  browser: string
  steps: Array<string>
  note?: string
}> = [
  {
    id: 'android',
    label: 'Android',
    icon: SmartphoneIcon,
    browser: 'Chrome',
    steps: [
      'Open nisaab.muhammadsaadcheema.com in Chrome.',
      'Tap the three dots at the top right.',
      'Tap "Add to Home screen", or "Install app" if it is offered.',
      'Confirm the name and tap Add.',
    ],
    note: 'Firefox and Samsung Internet work the same way, under the same menu.',
  },
  {
    id: 'ios',
    label: 'iPhone and iPad',
    icon: AppleIcon,
    browser: 'Safari',
    steps: [
      'Open the site in Safari. This does not work in Chrome on an iPhone.',
      'Tap the Share button, the square with an arrow coming out of it.',
      'Scroll down the list and tap "Add to Home Screen".',
      'Tap Add at the top right.',
    ],
    note: 'Apple allows this only from Safari, which is why the button above never appears on an iPhone.',
  },
  {
    id: 'windows',
    label: 'Windows',
    icon: MonitorIcon,
    browser: 'Edge or Chrome',
    steps: [
      'Open the site in Edge or Chrome.',
      'Look for the install icon in the address bar, a screen with an arrow in it.',
      'If it is not there: three dots, then Apps, then "Install this site as an app".',
      'Press Install. It appears in the Start menu like any other program.',
    ],
  },
  {
    id: 'macos',
    label: 'Mac',
    icon: AppleIcon,
    browser: 'Chrome, Edge or Safari 17+',
    steps: [
      'In Chrome or Edge: the install icon in the address bar, or three dots, then Cast, Save and Share, then Install.',
      'In Safari 17 and later: File, then "Add to Dock".',
      'It opens in its own window and lives in the Applications folder.',
    ],
  },
  {
    id: 'linux',
    label: 'Linux',
    icon: MonitorIcon,
    browser: 'Chrome or Chromium',
    steps: [
      'Open the site in Chrome, Chromium or Edge.',
      'Press the install icon in the address bar, or three dots, then "Install NISAAB".',
      'It is added to the applications menu as a desktop entry.',
    ],
    note: 'Firefox on Linux has no install option; a bookmark is the nearest thing.',
  },
]

/**
 * A guess at what the student is using, to open the right section first.
 *
 * `userAgent` is unreliable by design and is used here only to choose
 * which panel starts open. Every platform is listed either way, so being
 * wrong costs one tap rather than leaving somebody stuck.
 */
const guessPlatform = (): Platform => {
  if (typeof navigator === 'undefined') return 'windows'
  const ua = navigator.userAgent
  // iPadOS reports itself as a Mac, and is told apart by the touch points.
  const iPad = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1
  if (/iPhone|iPod/.test(ua) || iPad) return 'ios'
  if (/Android/.test(ua)) return 'android'
  if (/Macintosh|Mac OS X/.test(ua)) return 'macos'
  if (/Linux|X11/.test(ua)) return 'linux'
  return 'windows'
}

const Guide = ({
  guide,
  open,
  onToggle,
  mine,
}: {
  guide: (typeof GUIDES)[number]
  open: boolean
  onToggle: () => void
  mine: boolean
}) => {
  const Icon = guide.icon
  return (
    <div className="border-border/70 overflow-hidden rounded-lg border">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="hover:bg-muted/50 flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors"
      >
        <Icon className="text-muted-foreground size-4.5 shrink-0" />
        <span className="flex-1 text-sm font-medium">{guide.label}</span>
        {mine && <Badge variant="soft">You are on this</Badge>}
        <ChevronDownIcon
          className={cn(
            'text-muted-foreground size-4 shrink-0 transition-transform duration-200',
            open && 'rotate-180',
          )}
        />
      </button>
      {open && (
        <div className="border-border/70 border-t px-3 py-3">
          <p className="text-muted-foreground mb-2 text-xs">
            In {guide.browser}
          </p>
          <ol className="space-y-1.5">
            {guide.steps.map((step, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed">
                <span className="text-primary w-4 shrink-0 font-semibold tabular-nums">
                  {i + 1}.
                </span>
                <span className="min-w-0">{step}</span>
              </li>
            ))}
          </ol>
          {guide.note && (
            <p className="text-muted-foreground mt-2.5 text-xs leading-relaxed">
              {guide.note}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export const InstallAppSection = () => {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(
    typeof window === 'undefined'
      ? null
      : (window.__nisaabInstallPrompt ?? null),
  )
  const [installed, setInstalled] = useState(false)
  const [open, setOpen] = useState<Platform>(() => guessPlatform())
  const mine = guessPlatform()

  useEffect(() => {
    // Already running as an installed app: there is nothing to offer.
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      // Safari's own, which predates the standard and is still the only
      // way to tell on an iPhone.
      (navigator as { standalone?: boolean }).standalone === true
    if (standalone) setInstalled(true)

    const onPrompt = (event: Event) => {
      event.preventDefault()
      setPrompt(event as InstallPrompt)
    }
    const onInstalled = () => {
      setInstalled(true)
      setPrompt(null)
      window.__nisaabInstallPrompt = undefined
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  const install = async () => {
    if (!prompt) return
    await prompt.prompt()
    const { outcome } = await prompt.userChoice
    // The event is single-use: once shown it cannot be shown again, so
    // it is dropped either way and the written steps take over.
    setPrompt(null)
    window.__nisaabInstallPrompt = undefined
    if (outcome === 'accepted') setInstalled(true)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Install {brand.name}</CardTitle>
        <CardDescription>
          Put {brand.name} on your home screen or in your dock. It opens without
          the address bar, keeps you signed in, and takes almost no storage,
          because there is nothing to download.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {installed ? (
          <p className="border-accent-foreground/20 bg-accent text-accent-foreground flex items-center gap-2 rounded-lg border p-3 text-sm">
            <CheckCircle2Icon className="size-4 shrink-0" />
            Installed. You are using {brand.name} as an app.
          </p>
        ) : (
          <>
            {prompt && (
              <div className="space-y-2">
                <Button size="lg" onClick={() => void install()}>
                  <DownloadIcon />
                  Install {brand.name}
                </Button>
                <p className="text-muted-foreground text-xs">
                  Your browser can do this in one step.
                </p>
              </div>
            )}
            <div className="space-y-2">
              {!prompt && (
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Your browser does not offer a one-press install, so here is
                  how to do it by hand on every device.
                </p>
              )}
              {GUIDES.map((guide) => (
                <Guide
                  key={guide.id}
                  guide={guide}
                  open={open === guide.id}
                  mine={mine === guide.id}
                  onToggle={() =>
                    setOpen((was) =>
                      was === guide.id ? ('' as Platform) : guide.id,
                    )
                  }
                />
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
