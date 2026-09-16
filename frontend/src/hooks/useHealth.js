import { useEffect, useState } from 'react'
import { api } from '../services/api'

/**
 * One call on load. Drives the "backend not configured" banner and the
 * knowledge-base indicator in the header, so a missing GROQ_API_KEY is visible
 * before the user types a message rather than after.
 */
export function useHealth() {
  const [health, setHealth] = useState(null)
  const [reachable, setReachable] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .health()
      .then((data) => {
        if (!cancelled) {
          setHealth(data)
          setReachable(true)
        }
      })
      .catch(() => {
        if (!cancelled) setReachable(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { health, reachable }
}
