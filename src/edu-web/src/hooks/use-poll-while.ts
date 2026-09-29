import { useEffect, useState } from 'react'

/**
 * Calls `refresh` every `intervalMs` while `active` is true, for at most
 * `maxMs`. Returns true once polling gave up. Used while AI content is
 * being generated in the background.
 */
export const usePollWhile = (
  active: boolean,
  refresh: () => void,
  { intervalMs = 4000, maxMs = 180_000 } = {},
) => {
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!active) return
    setTimedOut(false)
    const started = Date.now()
    const timer = setInterval(() => {
      if (Date.now() - started > maxMs) {
        clearInterval(timer)
        setTimedOut(true)
        return
      }
      refresh()
    }, intervalMs)
    return () => clearInterval(timer)
  }, [active, refresh, intervalMs, maxMs])

  return timedOut
}
