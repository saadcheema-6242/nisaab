/**
 * The badge.
 *
 * Two kinds of thing get labelled with one of these, and they want
 * opposite treatment.
 *
 * A *result* - the grade on a finished paper, the count of teachers
 * waiting - is the loudest thing in its row on purpose, and `default`
 * stays a solid fill for exactly those.
 *
 * A *state* - Cancelled, Banned, Finished - is not. A red-filled chip
 * saying "Cancelled" next to a class title fights the title and makes a
 * routine cancellation look like an incident. Those variants are now
 * tinted surfaces with a matching border and coloured text, which is how
 * a status chip reads in a well-made table: legible, and quieter than
 * the thing it describes. `soft` is the same treatment in the brand
 * colour, for anything else that should sit back.
 *
 * Note the destructive text colour. It is `text-destructive` in both
 * themes rather than `destructive-foreground`, because that token is
 * near-black in the dark theme - correct against a solid red fill, and
 * invisible against a dark red tint.
 *
 * Letters are tracked out slightly. At 12px, where badges live, the extra
 * space is the difference between a word and a smudge.
 */

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva } from 'class-variance-authority'
import type { VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  [
    'inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden',
    'rounded-md border px-2 py-0.5',
    'text-xs font-medium tracking-[0.01em]',
    '[&>svg]:pointer-events-none [&>svg]:size-3',
    'transition-[color,box-shadow,background-color] duration-150 ease-out',
    'focus-visible:border-ring focus-visible:ring-ring/45 focus-visible:ring-[3px]',
    'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
  ].join(' '),
  {
    variants: {
      variant: {
        /** A result. Loud on purpose. */
        default:
          'border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90',
        /** The brand colour, sitting back. */
        soft: 'border-accent-foreground/20 bg-accent text-accent-foreground [a&]:hover:bg-accent/70',
        secondary:
          'border-secondary-foreground/15 bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/70',
        destructive:
          'border-destructive/30 bg-destructive/10 text-destructive focus-visible:ring-destructive/25 dark:bg-destructive/15 dark:focus-visible:ring-destructive/40 [a&]:hover:bg-destructive/15',
        outline:
          'border-border/70 text-muted-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<'span'> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'span'

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
