import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import clsx from 'clsx'
import { copyText } from '../lib/format'

/** Copy-to-clipboard control used for code blocks, replies and session ids. */
export function CopyButton({ value, label = 'Copy', className, iconOnly = false }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return undefined
    const timer = setTimeout(() => setCopied(false), 1600)
    return () => clearTimeout(timer)
  }, [copied])

  const handleCopy = async () => {
    const ok = await copyText(value)
    setCopied(ok)
  }

  const Icon = copied ? Check : Copy

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={clsx('btn-ghost', className)}
      aria-label={copied ? 'Copied' : label}
      title={copied ? 'Copied' : label}
    >
      <Icon size={14} strokeWidth={2} className={copied ? 'text-accent' : undefined} />
      {!iconOnly && <span>{copied ? 'Copied' : label}</span>}
    </button>
  )
}
