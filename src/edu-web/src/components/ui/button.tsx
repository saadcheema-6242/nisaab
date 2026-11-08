/**
 * The button.
 *
 * Stock shadcn gives a flat rectangle of colour that changes shade on
 * hover. It is fine and it is also the most-clicked thing in the app, so
 * it is where craft is noticed first.
 *
 * Three things were added, all of them about the button behaving like an
 * object rather than a coloured div:
 *
 *   a highlight along the top edge, which is what makes a solid shape read
 *   as catching light from above;
 *
 *   a shadow underneath that grows on hover, so the button appears to rise
 *   towards the pointer;
 *
 *   and on press the highlight becomes an inset shadow and the whole thing
 *   drops a pixel, so it is pushed in rather than merely recoloured.
 *
 * The shadow colours are written out rather than taken from the elevation
 * tokens because they sit against a saturated fill, not the page, and the
 * tokens are tuned for the page.
 *
 * Every one of these is suppressed under prefers-reduced-motion, which is
 * not a nicety: the exhibition laptop has it switched on.
 */

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva } from 'class-variance-authority'
import type { VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

/** Light from above on a filled button, and the pressed-in state. */
const RAISED = [
  'shadow-[inset_0_1px_0_0_rgb(255_255_255/0.16),0_1px_2px_-1px_rgb(16_38_30/0.28)]',
  'hover:shadow-[inset_0_1px_0_0_rgb(255_255_255/0.22),0_4px_10px_-3px_rgb(16_38_30/0.34)]',
  'hover:-translate-y-px',
  'active:translate-y-px active:shadow-[inset_0_1px_3px_0_rgb(0_0_0/0.22)]',
  // A button that keeps lifting while disabled is lying about being usable.
  'disabled:shadow-none disabled:translate-y-0',
  'motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:translate-y-0',
].join(' ')

const buttonVariants = cva(
  [
    'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap',
    'rounded-md text-sm font-medium',
    // 150ms out-easing: fast enough to feel like a response to the pointer
    // rather than an animation of its own.
    'transition-all duration-150 ease-out',
    'disabled:pointer-events-none disabled:opacity-50',
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
    'outline-none focus-visible:border-ring focus-visible:ring-ring/45 focus-visible:ring-[3px]',
    'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
  ].join(' '),
  {
    variants: {
      variant: {
        default: `bg-primary text-primary-foreground hover:bg-primary/92 ${RAISED}`,
        destructive: `bg-destructive text-white hover:bg-destructive/92 focus-visible:ring-destructive/25 dark:bg-destructive/60 dark:focus-visible:ring-destructive/40 ${RAISED}`,
        // Outline and secondary sit closer to the page, so they get the
        // page's own elevation tokens and a smaller lift.
        outline:
          'border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground hover:shadow-sm active:shadow-none dark:border-input dark:bg-input/30 dark:hover:bg-input/50',
        secondary:
          'bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80 hover:shadow-sm active:shadow-none',
        // Ghost and link have no surface, so there is nothing to raise.
        ghost:
          'hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 gap-1.5 rounded-md px-3 has-[>svg]:px-2.5',
        lg: 'h-10 rounded-md px-6 text-[0.9375rem] has-[>svg]:px-4',
        icon: 'size-9',
        'icon-sm': 'size-8',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
