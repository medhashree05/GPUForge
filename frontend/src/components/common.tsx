import { useState, type ReactNode } from 'react'
import type { PhaseResponse, PhaseStatus } from '../types/api'
import { STATUS_STYLE } from '../lib/phases'

export function StatusBadge({ status }: { status: PhaseStatus | 'idle' }) {
  const s = STATUS_STYLE[status]
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${s.text}`}>
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="btn-ghost"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
          setCopied(true)
          setTimeout(() => setCopied(false), 1200)
        } catch { /* clipboard unavailable */ }
      }}
    >
      {copied ? 'Copied' : label}
    </button>
  )
}

export function LoadingState({ label = 'Running Clang…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 p-6 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />
      {label}
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }: {
  title?: string; message: string; onRetry?: () => void
}) {
  return (
    <div role="alert" className="m-4 rounded-md border border-red-900/60 bg-red-950/40 p-4 text-sm">
      <div className="font-semibold text-red-300">{title}</div>
      <div className="mt-1 whitespace-pre-wrap text-red-200/90">{message}</div>
      {onRetry && <button type="button" className="btn mt-3" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="p-6 text-sm text-slate-500">{children}</div>
}

/** Status, message, warnings and the exact commands behind a phase result. */
export function PhaseHeader({ result, explanation }: { result: PhaseResponse; explanation?: string }) {
  const [showCmd, setShowCmd] = useState(false)
  return (
    <div className="space-y-2 border-b border-slate-800 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={result.status} />
        <span className="text-sm text-slate-300">{result.message}</span>
        {result.commands.length > 0 && (
          <button type="button" className="btn-ghost ml-auto" onClick={() => setShowCmd(!showCmd)}>
            {showCmd ? 'Hide' : 'Show'} commands ({result.commands.length})
          </button>
        )}
      </div>
      {explanation && <p className="text-xs leading-relaxed text-slate-500">{explanation}</p>}
      {result.warnings.map((w) => (
        <div key={w} className="rounded border border-amber-900/50 bg-amber-950/30 px-2 py-1 text-xs text-amber-200/90">
          {w}
        </div>
      ))}
      {showCmd && (
        <div className="space-y-1">
          {result.commands.map((c, i) => (
            <div key={i} className="font-mono text-[11px] text-slate-400">
              <span className="text-slate-600">$ </span>{c.command.join(' ')}
              <span className="text-slate-600">  # exit {c.exit_code}, {c.duration_ms} ms</span>
            </div>
          ))}
        </div>
      )}
      {result.status === 'failed' && result.compiler_stderr && (
        <details className="text-xs">
          <summary className="cursor-pointer text-slate-400">Raw compiler output</summary>
          <pre className="mt-1 max-h-48 overflow-auto rounded bg-slate-950 p-2 text-slate-300">{result.compiler_stderr}</pre>
        </details>
      )}
    </div>
  )
}

export function Explanations({ items, title }: {
  items: { opcode: string; count: number; explanation: string }[]; title: string
}) {
  if (!items.length) return null
  return (
    <div className="p-4">
      <h3 className="section-title">{title}</h3>
      <p className="mb-2 text-xs text-slate-500">Only instructions that occur in this output are listed.</p>
      <dl className="grid gap-x-4 gap-y-1.5 text-xs sm:grid-cols-[auto_1fr]">
        {items.map((e) => (
          <div key={e.opcode} className="contents">
            <dt className="font-mono text-sky-300">{e.opcode} <span className="text-slate-500">×{e.count}</span></dt>
            <dd className="text-slate-400">{e.explanation}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export function CountBars({ counts, max = 12 }: { counts: Record<string, number>; max?: number }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, max)
  const top = entries[0]?.[1] ?? 1
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate font-mono text-slate-300" title={k}>{k}</span>
          <span className="h-2 rounded-sm bg-sky-500/60" style={{ width: `${Math.max(4, (v / top) * 100)}%` }} />
          <span className="text-slate-500">{v}</span>
        </div>
      ))}
    </div>
  )
}
