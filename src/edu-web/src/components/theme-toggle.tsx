/**
 * Light and dark, where people look for it.
 *
 * The theme system was already complete - ThemeProvider handles light,
 * dark and system, remembers the choice, and every colour token has a
 * dark value - but the only way to reach it was a dropdown on the
 * settings page. Nobody goes to settings to change the look of an app
 * they have just opened.
 *
 * One button that cycles light, dark, system. Three states rather than a
 * switch, because "system" is a real answer and dropping it would mean a
 * student who keeps their phone on automatic night mode loses it.
 *
 * The label says what pressing it will do, not what the theme currently
 * is; a button is named for its action.
 */

import { MonitorIcon, MoonIcon, SunIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useTheme } from '@/providers/theme-provider'
import { cn } from '@/lib/utils'

const ORDER = ['light', 'dark', 'system'] as const

const LOOK = {
  light: { icon: SunIcon, now: 'Light', next: 'Switch to dark' },
  dark: { icon: MoonIcon, now: 'Dark', next: 'Follow the system' },
  system: { icon: MonitorIcon, now: 'System', next: 'Switch to light' },
} as const

export const ThemeToggle = ({ className }: { className?: string }) => {
  const { theme, setTheme } = useTheme()
  const current = (ORDER as ReadonlyArray<string>).includes(theme)
    ? (theme as (typeof ORDER)[number])
    : 'system'
  const { icon: Icon, now, next } = LOOK[current]

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'text-muted-foreground hover:text-foreground',
            className,
          )}
          // Said in full for a screen reader, which gets no tooltip.
          aria-label={`Theme: ${now}. ${next}.`}
          onClick={() =>
            setTheme(ORDER[(ORDER.indexOf(current) + 1) % ORDER.length])
          }
        >
          <Icon className="size-4.5" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{next}</TooltipContent>
    </Tooltip>
  )
}
