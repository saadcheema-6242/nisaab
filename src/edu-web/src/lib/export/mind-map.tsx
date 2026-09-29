import { fileSlug, renderOffscreen, saveBlob, toCanvas } from './core'
import type { MindMapNodeData } from '@/features/mind-map/components/mind-map-view'
import { MathText } from '@/components/math-text'
import { convertToTree } from '@/features/mind-map/components/mind-map-view'
import { brand } from '@/lib/brand'

type MapData = Parameters<typeof convertToTree>

const borderFor = (node: MindMapNodeData) =>
  node.form === 'formative'
    ? '1px dashed #9ca3af'
    : node.form === 'practical'
      ? '1px solid #f59e0b'
      : node.sloCode
        ? '1px solid #6366f1'
        : '1px solid #d1d5db'

// The whole tree, fully open, for printing and sharing
const StaticNode = ({ node, depth }: { node: MindMapNodeData; depth: number }) => (
  <div style={{ display: 'flex', alignItems: 'center' }}>
    <div
      style={{
        border: borderFor(node),
        borderRadius: 12,
        padding: depth === 0 ? '12px 18px' : '6px 12px',
        background: depth === 0 ? '#eef2ff' : '#ffffff',
        maxWidth: 300,
        fontSize: depth === 0 ? 18 : 13,
        fontWeight: depth <= 1 ? 600 : 500,
        flexShrink: 0,
      }}
    >
      <MathText>{node.label}</MathText>
      {node.sloCode && !node.label.startsWith(node.sloCode) && (
        <div style={{ fontSize: 10, color: '#6b7280', fontFamily: 'monospace' }}>{node.sloCode}</div>
      )}
    </div>
    {node.children && node.children.length > 0 && (
      <>
        <div style={{ width: 24, height: 1, background: '#d1d5db', flexShrink: 0 }} />
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            borderLeft: '1px solid #d1d5db',
            paddingLeft: 24,
          }}
        >
          {node.children.map((child) => (
            <StaticNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      </>
    )}
  </div>
)

export async function renderMap(title: string, nodes: MapData[0], edges: MapData[1]) {
  const tree = convertToTree(nodes, edges)
  if (!tree) throw new Error('This mind map is empty')
  return renderOffscreen(
    <div style={{ padding: 32 }}>
      <div style={{ fontSize: 12, color: '#6b7280' }}>{brand.name}</div>
      <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>{title}</div>
      <StaticNode node={tree} depth={0} />
    </div>,
    'auto',
  )
}

export async function exportMindMapPng(title: string, nodes: MapData[0], edges: MapData[1]) {
  const { element, cleanup } = await renderMap(title, nodes, edges)
  try {
    const canvas = await toCanvas(element, 2)
    const blob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Image failed'))), 'image/png'),
    )
    saveBlob(blob, `${fileSlug(title)}-mind-map.png`)
  } finally {
    cleanup()
  }
}

export async function exportMindMapPdf(title: string, nodes: MapData[0], edges: MapData[1]) {
  const { element, cleanup } = await renderMap(title, nodes, edges)
  try {
    const canvas = await toCanvas(element, 2)
    const { jsPDF } = await import('jspdf')
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'landscape' })
    const margin = 8
    const width = pdf.internal.pageSize.getWidth() - margin * 2
    const pageHeight = pdf.internal.pageSize.getHeight() - margin * 2
    // Fit the width; a tall map continues on further pages
    const scale = width / canvas.width
    const sliceHeight = Math.floor(pageHeight / scale)
    for (let top = 0, page = 0; top < canvas.height; top += sliceHeight, page++) {
      const slice = document.createElement('canvas')
      slice.width = canvas.width
      slice.height = Math.min(sliceHeight, canvas.height - top)
      const context = slice.getContext('2d')
      if (!context) throw new Error('Canvas not available')
      context.fillStyle = '#ffffff'
      context.fillRect(0, 0, slice.width, slice.height)
      context.drawImage(canvas, 0, top, canvas.width, slice.height, 0, 0, canvas.width, slice.height)
      if (page > 0) pdf.addPage()
      pdf.addImage(slice.toDataURL('image/jpeg', 0.92), 'JPEG', margin, margin, width, slice.height * scale)
    }
    pdf.save(`${fileSlug(title)}-mind-map.pdf`)
  } finally {
    cleanup()
  }
}
