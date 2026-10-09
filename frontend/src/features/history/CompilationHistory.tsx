import type { FullAnalysis, SourceRequest } from '../../types/api'

export interface HistoryEntry {
  id: number
  time: string
  request: SourceRequest
  result: FullAnalysis
}

/** Runs from the current browser session (kept in memory only). */
export function CompilationHistory({ entries, activeId, onRestore }: {
  entries: HistoryEntry[]; activeId: number | null; onRestore: (e: HistoryEntry) => void
}) {
  if (!entries.length) return <p className="px-3 text-xs text-slate-600">No runs yet.</p>
  return (
    <ul className="space-y-1 px-2">
      {entries.map((e) => {
        const ok = e.result.ir.status === 'success'
        // First line of real code (comments removed) identifies the run.
        const code = e.request.source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
        const first = code.split('\n').find((l) => l.trim()) ?? ''
        return (
          <li key={e.id}>
            <button type="button" onClick={() => onRestore(e)}
              className={`w-full rounded px-2 py-1 text-left text-[11px] hover:bg-slate-800 ${activeId === e.id ? 'bg-slate-800' : ''}`}>
              <div className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className="text-slate-300">{e.request.language.toUpperCase()} -{e.request.opt_level}</span>
                <span className="ml-auto text-slate-600">{e.time}</span>
              </div>
              <div className="truncate font-mono text-slate-500">{first.trim()}</div>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
