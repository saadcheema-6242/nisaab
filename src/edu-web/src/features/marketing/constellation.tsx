import { useEffect, useRef } from 'react'
import { subjects } from './site-data'
import { cn } from '@/lib/utils'

/**
 * The syllabus as a night sky: one point of light per learning outcome, in
 * five clusters whose sizes are the real SLO counts per subject.
 *
 * Drawn on a plain canvas with hand-rolled perspective projection rather than
 * WebGL: under a thousand points costs nothing to project, and it keeps the
 * landing page free of a 160 KB 3D dependency.
 */

type Point = {
  x: number
  y: number
  z: number
  size: number
  colour: string
  twinkle: number
}

type Link = { a: number; b: number; colour: string }

const DEPTH = 460 // camera distance; larger is a flatter perspective

/** Uniform-ish point inside a sphere, by rejection. */
const inSphere = (radius: number) => {
  for (;;) {
    const x = Math.random() * 2 - 1
    const y = Math.random() * 2 - 1
    const z = Math.random() * 2 - 1
    if (x * x + y * y + z * z <= 1) {
      return { x: x * radius, y: y * radius, z: z * radius }
    }
  }
}

const buildSky = (density: number) => {
  const points: Array<Point> = []
  const links: Array<Link> = []
  const ring = 150

  subjects.forEach((subject, index) => {
    const angle = (index / subjects.length) * Math.PI * 2
    const centre = {
      x: Math.cos(angle) * ring,
      y: Math.sin(angle * 2) * 34,
      z: Math.sin(angle) * ring,
    }
    const count = Math.max(8, Math.round(subject.slos * density))
    // a bigger subject gets a bigger cloud, but by volume so it stays readable
    const spread = 26 + Math.cbrt(subject.slos) * 11
    const first = points.length

    for (let i = 0; i < count; i += 1) {
      const offset = inSphere(spread)
      points.push({
        x: centre.x + offset.x,
        y: centre.y + offset.y,
        z: centre.z + offset.z,
        size: 0.7 + Math.random() * 1.5,
        colour: subject.colour,
        twinkle: Math.random() * Math.PI * 2,
      })
    }

    // join each star to a near neighbour so the cluster reads as a constellation
    const last = points.length
    for (let i = first; i < last; i += 1) {
      let best = -1
      let bestDist = Infinity
      for (let j = first; j < last; j += 1) {
        if (i === j) continue
        const p = points[i]
        const q = points[j]
        const d = (p.x - q.x) ** 2 + (p.y - q.y) ** 2 + (p.z - q.z) ** 2
        if (d < bestDist) {
          bestDist = d
          best = j
        }
      }
      if (best > i) links.push({ a: i, b: best, colour: subject.colour })
    }
  })

  return { points, links }
}

export const Constellation = ({ className }: { className?: string }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const small = window.innerWidth < 768
    // Phones draw a lighter sky; the shape stays the same.
    const { points, links } = buildSky(small ? 0.45 : 1)
    const order = points.map((_, i) => i)
    const projected = points.map(() => ({ x: 0, y: 0, k: 0, z: 0 }))

    let width = 0
    let height = 0
    let frame = 0
    let spin = 0

    // the pointer tilts the sky a little, so it feels like a window not a video
    let aimX = 0
    let aimY = 0
    let tiltX = 0
    let tiltY = 0

    const draw = (time: number) => {
      spin += still ? 0 : 0.0012
      tiltX += (aimY * 0.22 - tiltX) * 0.045
      tiltY += (aimX * 0.42 - tiltY) * 0.045

      const ry = spin + tiltY
      const rx = -0.17 + tiltX
      const cosY = Math.cos(ry)
      const sinY = Math.sin(ry)
      const cosX = Math.cos(rx)
      const sinX = Math.sin(rx)
      const cx = width / 2
      const cy = height / 2
      const scale = Math.min(width, height) / 520

      for (let i = 0; i < points.length; i += 1) {
        const p = points[i]
        const x1 = p.x * cosY - p.z * sinY
        const z1 = p.x * sinY + p.z * cosY
        const y2 = p.y * cosX - z1 * sinX
        const z2 = p.y * sinX + z1 * cosX
        const k = (DEPTH / (DEPTH + z2)) * scale
        const out = projected[i]
        out.x = cx + x1 * k
        out.y = cy + y2 * k
        out.k = k
        out.z = z2
      }

      ctx.clearRect(0, 0, width, height)
      ctx.globalCompositeOperation = 'lighter'

      // links first, so the stars sit on top of their own threads
      ctx.lineWidth = 0.6
      for (const link of links) {
        const a = projected[link.a]
        const b = projected[link.b]
        const depth = (a.k + b.k) / 2 / scale
        ctx.globalAlpha = Math.max(0, Math.min(0.2, (depth - 0.55) * 0.3))
        ctx.strokeStyle = link.colour
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }

      order.sort((i, j) => projected[j].z - projected[i].z)
      for (const i of order) {
        const p = points[i]
        const q = projected[i]
        const depth = q.k / scale
        const flicker = still
          ? 1
          : 0.78 + Math.sin(time * 0.0014 + p.twinkle) * 0.22
        const radius = Math.max(0.35, p.size * q.k * 0.52)
        ctx.fillStyle = p.colour

        ctx.globalAlpha =
          Math.max(0, Math.min(0.85, (depth - 0.45) * 0.95)) * flicker
        ctx.beginPath()
        ctx.arc(q.x, q.y, radius, 0, Math.PI * 2)
        ctx.fill()

        ctx.globalAlpha *= 0.14 // halo
        ctx.beginPath()
        ctx.arc(q.x, q.y, radius * 3.6, 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = 'source-over'
      if (!still) frame = requestAnimationFrame(draw)
    }

    // Setting canvas.width clears the bitmap, so every resize has to repaint —
    // otherwise a reduced-motion visitor, who only ever gets one frame, is left
    // looking at an empty canvas.
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      width = rect.width
      height = rect.height
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      if (still) {
        cancelAnimationFrame(frame)
        frame = requestAnimationFrame(draw)
      }
    }

    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)

    const onPointer = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect()
      aimX = ((event.clientX - rect.left) / rect.width - 0.5) * 2
      aimY = ((event.clientY - rect.top) / rect.height - 0.5) * 2
    }
    if (!still) {
      window.addEventListener('pointermove', onPointer, { passive: true })
      frame = requestAnimationFrame(draw)
    }

    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('pointermove', onPointer)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={cn('size-full', className)}
    />
  )
}
