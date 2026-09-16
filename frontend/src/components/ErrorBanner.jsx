import { AlertTriangle, X } from 'lucide-react'
import clsx from 'clsx'

/**
 * Errors state what happened and what to do about it. They never show a stack
 * trace — the backend keeps those in its own log.
 */
export function ErrorBanner({ message, onDismiss, onRetry, tone = 'danger' }) {
  if (!message) return null

  return (
    <div
      role="alert"
      className={clsx(
        'mx-auto flex w-full max-w-thread items-start gap-3 rounded-lg border px-4 py-2.5 text-[13px]',
        tone === 'danger'
          ? 'border-danger bg-danger-soft text-ink'
          : 'border-hairline bg-grounded-soft text-ink',
      )}
    >
      <AlertTriangle
        size={15}
        className={clsx('mt-0.5 shrink-0', tone === 'danger' ? 'text-danger' : 'text-grounded')}
      />
      <p className="flex-1 leading-relaxed">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="shrink-0 font-medium text-accent hover:underline">
          Try again
        </button>
      )}
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="btn-ghost !p-1" aria-label="Dismiss">
          <X size={14} />
        </button>
      )}
    </div>
  )
}
