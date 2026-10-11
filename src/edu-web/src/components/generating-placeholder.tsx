import { ThinkingDots } from '@/components/ui/thinking-dots'

export const GeneratingPlaceholder = ({
  what,
  timedOut,
}: {
  what: string
  timedOut: boolean
}) => (
  <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
    {timedOut ? (
      <span>No {what} yet. Refresh the page in a minute.</span>
    ) : (
      <>
        <ThinkingDots className="mb-1" label={`Preparing your ${what}`} />
        <span className="thinking-text font-medium text-foreground">
          Preparing your {what}…
        </span>
        <span className="text-sm">This usually takes under a minute.</span>
      </>
    )}
  </div>
)
