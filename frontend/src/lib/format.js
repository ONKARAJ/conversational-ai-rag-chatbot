/** Presentation helpers shared across components. */

/** "Just now" / "14m ago" / "Yesterday" / "12 Mar" */
export function relativeTime(value) {
  if (!value) return ''
  const then = new Date(value)
  if (Number.isNaN(then.getTime())) return ''

  const seconds = Math.round((Date.now() - then.getTime()) / 1000)
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 172_800) return 'Yesterday'
  if (seconds < 604_800) return `${Math.floor(seconds / 86_400)}d ago`

  return then.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export function clockTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

/** Buckets for the sidebar: Today / Previous 7 days / Earlier. */
export function groupByRecency(conversations) {
  const groups = [
    { label: 'Today', items: [] },
    { label: 'Previous 7 days', items: [] },
    { label: 'Earlier', items: [] },
  ]
  const now = Date.now()

  conversations.forEach((conversation) => {
    const age = now - new Date(conversation.updated_at).getTime()
    if (age < 86_400_000) groups[0].items.push(conversation)
    else if (age < 604_800_000) groups[1].items.push(conversation)
    else groups[2].items.push(conversation)
  })

  return groups.filter((group) => group.items.length > 0)
}

export function shortId(conversationId = '') {
  return conversationId.replace('conversation_', '').slice(0, 8)
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Clipboard API needs a secure context; fall back to a temporary textarea.
    try {
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(area)
      return ok
    } catch {
      return false
    }
  }
}
