import { useEffect, useState } from 'react'

/**
 * True once `ms` have passed since this mounted, so a wait that runs long can
 * say so instead of leaving the student wondering.
 */
export const useSlowAfter = (ms = 8000) => {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), ms)
    return () => clearTimeout(timer)
  }, [ms])

  return slow
}
