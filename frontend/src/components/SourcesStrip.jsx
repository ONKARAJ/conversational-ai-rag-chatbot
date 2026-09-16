import { useState } from 'react'
import { BookText, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

/**
 * Provenance for a grounded answer: which knowledge-base chunks the retriever
 * returned for this question. Collapsed by default — it is evidence, not
 * decoration — and the one place the brass accent is used.
 */
export function SourcesStrip({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources?.length) return null

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex items-center gap-1.5 rounded-md bg-grounded-soft px-2 py-1 text-xs
                   font-medium text-grounded transition-colors hover:brightness-110"
        aria-expanded={open}
      >
        <BookText size={13} strokeWidth={2} />
        <span>
          {sources.length} retrieved {sources.length === 1 ? 'passage' : 'passages'}
        </span>
        <ChevronDown size={13} className={clsx('transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <ul className="mt-2 space-y-2 animate-fade-in">
          {sources.map((source, index) => (
            <li
              key={`${source.source}-${index}`}
              className="rounded-lg border border-hairline bg-surface px-3 py-2"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-xs text-grounded">{source.source}</span>
                {typeof source.score === 'number' && (
                  <span className="font-mono text-[11px] text-faint">
                    {source.score.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-muted">{source.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
