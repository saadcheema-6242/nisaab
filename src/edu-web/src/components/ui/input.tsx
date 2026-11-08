/**
 * The text field.
 *
 * The one place in the app where a person is doing the work rather than
 * reading, so the field has to say clearly where the caret is. Stock
 * shadcn fades a 3px ring in on focus and leaves the fill unchanged, which
 * on a form of six fields is surprisingly hard to track.
 *
 * Changes:
 *
 *   The resting field is tinted away from the card instead of transparent,
 *   so it reads as a recess waiting for input rather than as a rectangle
 *   drawn on the surface, and an empty form looks like a form.
 *
 *   On focus the fill goes to the card colour and the ring comes up, so
 *   the active field is the one that lifts out of the page. Two signals
 *   agreeing, which is what makes it findable at a glance.
 *
 *   The caret is the brand green. A small thing that is on screen the
 *   entire time someone is typing.
 *
 * Text stays at 16px on small screens. Anything smaller makes iOS Safari
 * zoom the page on focus, which looks like a bug to anyone holding a phone.
 */

import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'border-input h-9 w-full min-w-0 rounded-md border px-3 py-1',
        'text-base md:text-sm',
        'caret-primary placeholder:text-muted-foreground/80',
        'selection:bg-primary selection:text-primary-foreground',
        'file:text-foreground file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium',
        // The recess, and the lift out of it on focus.
        'bg-muted/40 shadow-[inset_0_1px_2px_0_rgb(16_38_30/0.05)] dark:bg-input/30',
        'transition-[color,box-shadow,background-color,border-color] duration-150 ease-out',
        'outline-none',
        'hover:border-ring/45',
        'focus-visible:bg-card focus-visible:border-ring focus-visible:ring-ring/45 focus-visible:ring-[3px] focus-visible:shadow-none',
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
        'motion-reduce:transition-none',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
