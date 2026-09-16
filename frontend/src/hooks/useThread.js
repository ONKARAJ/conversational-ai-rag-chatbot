import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

/**
 * Owns one conversation's transcript.
 *
 * Sending is optimistic: the user's message appears instantly with a temporary
 * id, then is replaced by the persisted row from the server. If the request
 * fails, the optimistic message is rolled back and the text is handed back to
 * the composer so nothing the user typed is lost.
 */
export function useThread(conversationId, { onReply } = {}) {
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [sourcesByMessage, setSourcesByMessage] = useState({})
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  const sendingRef = useRef(false) // guards against double submits
  const replyRef = useRef(onReply)
  replyRef.current = onReply

  useEffect(() => {
    if (!conversationId) {
      setConversation(null)
      setMessages([])
      setSourcesByMessage({})
      return undefined
    }

    const controller = new AbortController()
    setLoading(true)
    setError(null)

    api
      .getConversation(conversationId, { signal: controller.signal })
      .then((data) => {
        setConversation(data)
        setMessages(data.messages ?? [])
        setSourcesByMessage({})
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        setError(err.message)
        setMessages([])
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort('conversation-changed')
  }, [conversationId])

  const send = useCallback(
    async (text) => {
      const content = text.trim()
      if (!content || !conversationId || sendingRef.current) return { ok: false }

      sendingRef.current = true
      setSending(true)
      setError(null)

      const optimistic = {
        id: `pending-${Date.now()}`,
        role: 'human',
        content,
        created_at: new Date().toISOString(),
        pending: true,
      }
      setMessages((current) => [...current, optimistic])

      try {
        const result = await api.sendMessage(conversationId, { content })

        setMessages((current) => [
          ...current.filter((message) => message.id !== optimistic.id),
          result.user_message,
          result.assistant_message,
        ])

        if (result.sources?.length) {
          setSourcesByMessage((current) => ({
            ...current,
            [result.assistant_message.id]: result.sources,
          }))
        }

        setConversation((current) => (current ? { ...current, title: result.title } : current))
        replyRef.current?.({ title: result.title })
        return { ok: true }
      } catch (err) {
        setMessages((current) => current.filter((message) => message.id !== optimistic.id))
        setError(err.message)
        return { ok: false, restore: content }
      } finally {
        sendingRef.current = false
        setSending(false)
      }
    },
    [conversationId],
  )

  return {
    conversation,
    messages,
    sourcesByMessage,
    loading,
    sending,
    error,
    clearError: () => setError(null),
    send,
  }
}
