import type { DiagnosticsResponse } from '../../types/api'
import { PhaseHeader } from '../../components/common'

const SEV: Record<string, string> = {
  error: 'text-red-300 border-red-800/60',
  'fatal error': 'text-red-300 border-red-800/60',
  warning: 'text-amber-300 border-amber-800/60',
  note: 'text-sky-300 border-slate-700',
  remark: 'text-slate-300 border-slate-700',
}

export function DiagnosticsPanel({ data, onFocusLine, explanation }: {
  data: DiagnosticsResponse; onFocusLine: (l: number) => void; explanation: string
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      <div className="min-h-0 flex-1 space-y-2 overflow-auto p-4">
        {data.semantic_ok && data.diagnostics.length === 0 && (
          <div className="rounded border border-emerald-900/50 bg-emerald-950/30 p-3 text-sm text-emerald-200">
            Clang parsed the program and semantic analysis reported no errors or warnings
            (with -Wall -Wextra). Code generation is attempted in the next phases.
          </div>
        )}
        {data.diagnostics.map((d, i) => (
          <button
            key={i} type="button"
            className={`block w-full rounded border bg-slate-900/60 p-3 text-left ${SEV[d.severity] ?? ''} ${d.severity === 'note' ? 'ml-6 w-[calc(100%-1.5rem)]' : ''}`}
            onClick={() => d.line && onFocusLine(d.line)}
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold uppercase">{d.severity}</span>
              {d.line !== null && <span className="text-slate-400">line {d.line}:{d.column}</span>}
              {d.category && <span className="rounded bg-slate-800 px-1.5 text-slate-300">{d.category}</span>}
              {d.flag && <span className="font-mono text-slate-500">{d.flag}</span>}
              {!d.in_main_file && <span className="text-slate-500">(in a header)</span>}
            </div>
            <div className="mt-1 text-sm text-slate-100">{d.message}</div>
            {d.snippet && (
              <pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-2 font-mono text-xs text-slate-300">
                {d.snippet}
                {d.column ? `\n${' '.repeat(Math.max(0, d.column - 1))}^` : ''}
              </pre>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
