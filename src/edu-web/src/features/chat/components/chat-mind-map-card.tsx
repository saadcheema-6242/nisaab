import { Result, useAtomValue } from '@effect-atom/atom-react'
import { Link } from '@tanstack/react-router'
import { ChevronRightIcon, Loader2Icon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { mindMapAtom } from '@/data-acess/mind-map'
import { MindMapView } from '@/features/mind-map/components/mind-map-view'
import { MindMapDownload } from '@/components/downloads'

type MapData = Parameters<typeof MindMapView>[0]['mapData']

/** A visual mind map inside the chat; tapping a node offers Explain / Practise. */
export const ChatMindMapCard = ({
  projectId,
  mindMapId,
  onAsk,
}: {
  projectId: string
  mindMapId: string
  onAsk?: (text: string) => void
}) => {
  const result = useAtomValue(mindMapAtom(`${projectId}:${mindMapId}`))
  const mindMap = Result.isSuccess(result) ? result.value : null

  return (
    <div className="w-full max-w-3xl overflow-hidden rounded-xl border bg-card">
      <div className="flex flex-wrap items-center gap-2 border-b p-3">
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{mindMap?.title ?? 'Mind map'}</div>
          {mindMap?.description && (
            <div className="text-xs text-muted-foreground">
              {mindMap.description}
            </div>
          )}
        </div>
        <MindMapDownload projectId={projectId} mindMapId={mindMapId} />
        <Button size="sm" variant="ghost" asChild>
          <Link
            to="/dashboard/p/$projectId/m/$mindMapId"
            params={{ projectId, mindMapId }}
          >
            Full screen
            <ChevronRightIcon className="size-4" />
          </Link>
        </Button>
      </div>
      {mindMap ? (
        <MindMapView
          mapData={mindMap.map_data as MapData}
          onAsk={onAsk}
          className="h-[26rem]"
        />
      ) : Result.isFailure(result) ? (
        <p className="p-4 text-sm text-destructive">
          Could not load the mind map
        </p>
      ) : (
        <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" />
          Loading mind map…
        </div>
      )}
    </div>
  )
}
