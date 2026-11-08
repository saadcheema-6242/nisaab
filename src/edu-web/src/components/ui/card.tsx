/**
 * The card.
 *
 * Almost every surface in the app is a grid of these, so a card that reads
 * as a bordered rectangle makes the whole product read as a bordered
 * rectangle. Two changes:
 *
 * The resting shadow moved from shadow-sm to shadow-xs, and the border
 * lightened. A card does not need both a hard line and a shadow to be
 * separate from the page; using both is what makes an interface look
 * boxed-in. The shadow now does the separating and the border only keeps
 * the edge crisp.
 *
 * And a card may now be interactive. Pass `interactive` to a card that is
 * a link or a button and it lifts under the pointer, which is the only
 * honest way to say "this is clickable" without printing the word.
 *
 * The title is deliberately left in the sans face. The serif is for page
 * titles; applying it here would put it at 16px, where it stops looking
 * considered and starts looking like a mistake.
 */

import * as React from 'react'

import { cn } from '@/lib/utils'

function Card({
  className,
  interactive = false,
  ...props
}: React.ComponentProps<'div'> & {
  /** Set on a card that is itself a link or a button. */
  interactive?: boolean
}) {
  return (
    <div
      data-slot="card"
      data-interactive={interactive || undefined}
      className={cn(
        'bg-card text-card-foreground flex flex-col gap-6 rounded-xl py-6',
        'border-border/70 border shadow-xs',
        interactive && [
          'cursor-pointer transition-all duration-200 ease-out',
          'hover:border-border hover:-translate-y-0.5 hover:shadow-md',
          // A card is large, so it needs a focus ring of its own; the
          // shadow change alone is invisible to a keyboard user.
          'focus-visible:ring-ring/45 focus-visible:outline-none focus-visible:ring-[3px]',
          'active:translate-y-0 active:shadow-sm',
          'motion-reduce:transition-none motion-reduce:hover:translate-y-0',
        ],
        className,
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6',
        className,
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-title"
      className={cn(
        'font-semibold leading-tight tracking-[-0.006em]',
        className,
      )}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-description"
      className={cn('text-muted-foreground text-sm leading-relaxed', className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        'col-start-2 row-span-2 row-start-1 self-start justify-self-end',
        className,
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-content"
      className={cn('px-6', className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex items-center px-6 [.border-t]:pt-6', className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
