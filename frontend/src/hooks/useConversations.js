import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

/**
 * Owns the sidebar list. The backend is the source of truth; this hook keeps
 * a local copy so the UI can update immediately after a rename or delete
 * without refetching the whole list.
 */
export function useConversations(search) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const requestRef = useRef(0)

  const load = useCallback(
    async (query) => {
      const requestId = ++requestRef.current
      setLoading(true)
      try {
        const data = await api.listConversations(query)
        // Ignore responses from a superseded search keystroke.
        if (requestId !== requestRef.current) return
        setConversations(data)
        setError(null)
      } catch (err) {
        if (requestId !== requestRef.current) return
        setError(err.message)
      } finally {
        if (requestId === requestRef.current) setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    const timer = setTimeout(() => load(search), search ? 250 : 0)
    return () => clearTimeout(timer)
  }, [search, load])

  const create = useCallback(async () => {
    const conversation = await api.createConversation({})
    setConversations((current) => [conversation, ...current])
    return conversation
  }, [])

  const rename = useCallback(async (id, title) => {
    const updated = await api.updateConversation(id, { title })
    setConversations((current) => current.map((c) => (c.id === id ? { ...c, ...updated } : c)))
    return updated
  }, [])

  const remove = useCallback(async (id) => {
    await api.deleteConversation(id)
    setConversations((current) => current.filter((c) => c.id !== id))
  }, [])

  /** Called after a reply lands so the item jumps to the top of the list. */
  const touch = useCallback((id, patch = {}) => {
    setConversations((current) => {
      const index = current.findIndex((c) => c.id === id)
      if (index === -1) return current
      const updated = {
        ...current[index],
        ...patch,
        updated_at: new Date().toISOString(),
      }
      const rest = current.filter((c) => c.id !== id)
      return [updated, ...rest]
    })
  }, [])

  return { conversations, loading, error, reload: () => load(search), create, rename, remove, touch }
}
