/**
 * The only place in the frontend that talks to the network.
 *
 * Requests go to a relative /api path. In development Vite proxies that to
 * FastAPI on :8000 (see vite.config.js); in production you would put both
 * behind the same origin. Either way the browser never holds an API key —
 * GROQ_API_KEY lives on the server and nowhere else.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_TIMEOUT_MS = 90_000 // model answers can legitimately take a while

export class ApiError extends Error {
  constructor(message, { code = 'unknown_error', status = 0 } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

async function request(path, { method = 'GET', body, signal, timeout = DEFAULT_TIMEOUT_MS } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort('timeout'), timeout)

  // Let callers cancel too (e.g. switching conversations mid-load).
  if (signal) signal.addEventListener('abort', () => controller.abort(signal.reason))

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (error) {
    clearTimeout(timer)
    if (signal?.aborted) throw error
    if (controller.signal.reason === 'timeout') {
      throw new ApiError('The request timed out. The model may still be busy — try again.', {
        code: 'timeout',
      })
    }
    throw new ApiError('Cannot reach the backend. Is it running on port 8000?', {
      code: 'network_error',
    })
  } finally {
    clearTimeout(timer)
  }

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const detail = payload?.error ?? {}
    throw new ApiError(detail.message || `Request failed (${response.status}).`, {
      code: detail.code || 'http_error',
      status: response.status,
    })
  }

  return payload
}

export const api = {
  health: () => request('/api/health', { timeout: 10_000 }),

  listConversations: (search, options) =>
    request(`/api/conversations${search ? `?search=${encodeURIComponent(search)}` : ''}`, {
      timeout: 15_000,
      ...options,
    }),

  createConversation: (payload = {}) =>
    request('/api/conversations', { method: 'POST', body: payload, timeout: 15_000 }),

  getConversation: (id, options) =>
    request(`/api/conversations/${id}`, { timeout: 15_000, ...options }),

  updateConversation: (id, payload) =>
    request(`/api/conversations/${id}`, { method: 'PATCH', body: payload, timeout: 15_000 }),

  deleteConversation: (id) =>
    request(`/api/conversations/${id}`, { method: 'DELETE', timeout: 15_000 }),

  sendMessage: (id, payload) =>
    request(`/api/conversations/${id}/messages`, { method: 'POST', body: payload }),
}
