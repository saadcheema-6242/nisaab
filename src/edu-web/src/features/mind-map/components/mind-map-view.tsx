import { useMemo, useState } from 'react'
import {
  BookOpenIcon,
  ChevronRight,
  Circle,
  ListChecksIcon,
  MinusIcon,
  PlusIcon,
  ScanIcon,
  XIcon,
} from 'lucide-react'
import { MathText } from '@/components/math-text'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { assessmentForms } from '@/features/syllabus/slo-labels'
import { cn } from '@/lib/utils'

// --- Types ---

export interface MindMapNodeData {
  id: string
  label: string
  content?: string
  sloCode?: string
  form?: 'summative' | 'formative' | 'practical' | 'unknown'
  children?: Array<MindMapNodeData>
}

type RawNode = {
  id: string
  type?: string
  position?: { x: number; y: number }
  data: { label: string; [key: string]: unknown }
}
type RawEdge = {
  id: string
  source: string
  target: string
  label?: string | null
  type?: string
}

// Converts the stored nodes/edges into a tree
export function convertToTree(
  nodes: Array<RawNode>,
  edges: Array<RawEdge>,
): MindMapNodeData | null {
  if (nodes.length === 0) {
    return null
  }

  const nodeMap = new Map<string, MindMapNodeData>()
  const childrenMap = new Map<string, Array<string>>()

  nodes.forEach((node) => {
    nodeMap.set(node.id, {
      id: node.id,
      label: node.data.label,
      content: (node.data.content as string | null | undefined) ?? undefined,
      sloCode: (node.data.slo_code as string | null | undefined) ?? undefined,
      form: (node.data.form as MindMapNodeData['form'] | null | undefined) ?? undefined,
      children: [],
    })
    childrenMap.set(node.id, [])
  })

  edges.forEach((edge) => {
    const children = childrenMap.get(edge.source) || []
    children.push(edge.target)
    childrenMap.set(edge.source, children)
  })

  const buildNode = (nodeId: string): MindMapNodeData | null => {
    const node = nodeMap.get(nodeId)
    if (!node) return null
    const childIds = childrenMap.get(nodeId) || []
    node.children = childIds
      .map((childId) => buildNode(childId))
      .filter((child): child is MindMapNodeData => child !== null)
    return node
  }

  const targetIds = new Set(edges.map((e) => e.target))
  const rootNodes = nodes.filter((node) => !targetIds.has(node.id))

  if (rootNodes.length === 0) {
    return buildNode(nodes[0].id)
  }

  if (rootNodes.length > 1) {
    return {
      id: 'root',
      label: 'Root',
      children: rootNodes
        .map((node) => buildNode(node.id))
        .filter((node): node is MindMapNodeData => node !== null),
    }
  }

  return buildNode(rootNodes[0].id)
}

const formStyles: Record<NonNullable<MindMapNodeData['form']>, string> = {
  summative: 'border-primary/50 bg-primary/5',
  formative: 'border-dashed border-muted-foreground/40',
  practical: 'border-amber-500/60 bg-amber-500/5',
  unknown: '',
}

// --- Recursive node ---

const MindMapNode = ({
  data,
  depth,
  openDepth,
  selectedId,
  onSelect,
}: {
  data: MindMapNodeData
  depth: number
  openDepth: number
  selectedId: string | null
  onSelect: (node: MindMapNodeData) => void
}) => {
  const [isExpanded, setIsExpanded] = useState(depth < openDepth)
  const hasChildren = !!data.children && data.children.length > 0
  const isRoot = depth === 0
  const selected = selectedId === data.id

  return (
    <div className="flex flex-row items-center">
      <div className="relative z-10 flex items-center">
        <div
          role="button"
          tabIndex={0}
          onClick={() => onSelect(data)}
          onKeyDown={(e) => e.key === 'Enter' && onSelect(data)}
          className={cn(
            'group flex max-w-[280px] cursor-pointer items-center gap-2 rounded-xl border bg-card text-card-foreground shadow-sm transition-all duration-200',
            isRoot ? 'px-5 py-3 border-primary/40' : 'px-3 py-2 hover:border-primary/50 hover:shadow-md',
            data.form && formStyles[data.form],
            selected && 'ring-2 ring-primary',
          )}
        >
          {hasChildren && (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 shrink-0"
              onClick={(e) => {
                e.stopPropagation()
                setIsExpanded(!isExpanded)
              }}
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              <ChevronRight
                className={cn('h-3.5 w-3.5 transition-transform', isExpanded && 'rotate-90')}
              />
            </Button>
          )}
          {!hasChildren && !isRoot && (
            <Circle size={8} className="shrink-0 fill-current text-primary" />
          )}
          <div className="flex min-w-0 flex-col">
            <MathText
              className={cn(
                'font-medium break-words [&_p]:my-0',
                isRoot ? 'text-base' : 'text-sm',
              )}
            >
              {data.label}
            </MathText>
            {data.sloCode && !data.label.startsWith(data.sloCode) && (
              <span className="font-mono text-[10px] text-muted-foreground">{data.sloCode}</span>
            )}
          </div>
        </div>
        {hasChildren && isExpanded && <div className="h-px w-8 bg-border" />}
      </div>

      {hasChildren && isExpanded && (
        <div className="relative ml-0 flex flex-col gap-3 border-l border-border py-2 pl-8">
          {data.children?.map((child, index) => (
            <div key={child.id} className="relative">
              <div className="absolute -left-8 top-1/2 h-px w-8 bg-border" />
              {index === 0 && (
                <div className="absolute -left-[33px] -top-3 h-1/2 w-1 bg-background" />
              )}
              {index === data.children!.length - 1 && (
                <div className="absolute -left-[33px] top-1/2 h-full w-1 bg-background" />
              )}
              <MindMapNode
                data={child}
                depth={depth + 1}
                openDepth={openDepth}
                selectedId={selectedId}
                onSelect={onSelect}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Details of the selected node ---

const NodeDetails = ({
  node,
  onClose,
  onAsk,
}: {
  node: MindMapNodeData
  onClose: () => void
  onAsk?: (text: string) => void
}) => (
  <div className="space-y-2 border-t bg-card p-3 text-sm">
    <div className="flex items-start gap-2">
      <MathText className="flex-1 font-semibold">{node.label}</MathText>
      <button type="button" onClick={onClose} aria-label="Close details">
        <XIcon className="size-4 text-muted-foreground" />
      </button>
    </div>
    {node.sloCode && (
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono">
          SLO {node.sloCode}
        </Badge>
        {node.form && (
          <span className="text-xs text-muted-foreground">
            {assessmentForms[node.form].label}
          </span>
        )}
      </div>
    )}
    {node.content && <MathText className="text-muted-foreground">{node.content}</MathText>}
    {onAsk && (
      <div className="flex flex-wrap gap-2 pt-1">
        <Button
          size="sm"
          variant="outline"
          onClick={() =>
            onAsk(
              `Explain "${node.label}"${node.sloCode ? ` (SLO ${node.sloCode})` : ''} in detail.`,
            )
          }
        >
          <BookOpenIcon className="size-4" />
          Explain
        </Button>
        {node.sloCode && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onAsk(`Give me a 5 MCQ quiz on SLO ${node.sloCode}.`)}
          >
            <ListChecksIcon className="size-4" />
            Practise
          </Button>
        )}
      </div>
    )}
  </div>
)

// --- Container ---

type MindMapViewProps = {
  mapData: { nodes: Array<RawNode>; edges: Array<RawEdge> }
  // Explain / Practise buttons send a chat message (only inside a chat)
  onAsk?: (text: string) => void
  className?: string
}

const ZOOM_STEPS = [0.6, 0.75, 0.9, 1, 1.15, 1.3]

export const MindMapView = ({ mapData, onAsk, className }: MindMapViewProps) => {
  const rootNode = useMemo(
    () => convertToTree(mapData.nodes, mapData.edges),
    [mapData.nodes, mapData.edges],
  )
  const [zoom, setZoom] = useState(3)
  const [selected, setSelected] = useState<MindMapNodeData | null>(null)

  if (!rootNode) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        <p>No mind map data available</p>
      </div>
    )
  }

  // Big maps open one level deep; the student opens the branches they want
  const openDepth = mapData.nodes.length > 25 ? 1 : 3
  const scale = ZOOM_STEPS[zoom]

  return (
    <div className={cn('relative flex h-full w-full flex-col bg-background', className)}>
      <div className="absolute right-2 top-2 z-20 flex gap-1 rounded-lg border bg-background/90 p-1 shadow-sm">
        <Button
          size="icon"
          variant="ghost"
          className="size-7"
          disabled={zoom === 0}
          onClick={() => setZoom(zoom - 1)}
          aria-label="Zoom out"
        >
          <MinusIcon className="size-4" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          className="size-7"
          onClick={() => setZoom(3)}
          aria-label="Reset zoom"
        >
          <ScanIcon className="size-4" />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          className="size-7"
          disabled={zoom === ZOOM_STEPS.length - 1}
          onClick={() => setZoom(zoom + 1)}
          aria-label="Zoom in"
        >
          <PlusIcon className="size-4" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <div
          className="flex min-w-full origin-top-left flex-col p-6"
          style={{ transform: `scale(${scale})`, width: `${100 / scale}%` }}
        >
          <div className="flex items-center justify-start">
            <MindMapNode
              data={rootNode}
              depth={0}
              openDepth={openDepth}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
          </div>
        </div>
      </div>
      {selected && (
        <NodeDetails node={selected} onClose={() => setSelected(null)} onAsk={onAsk} />
      )}
    </div>
  )
}
