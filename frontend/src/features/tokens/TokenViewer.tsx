import { useMemo, useState } from 'react'
import type { TokensResponse } from '../../types/api'
import { PhaseHeader } from '../../components/common'

export function TokenViewer({ data, onFocusLine, explanation }: {
  data: TokensResponse; onFocusLine: (line: number) => void; explanation: string
}) {
  const [kind, setKind] = useState('')
  const [query, setQuery] = useState('')
  const rows = useMemo(() => data.tokens.filter((t) =>
    (!kind || t.kind === kind) && (!query || t.text.toLowerCase().includes(query.toLowerCase()))),
  [data.tokens, kind, query])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      <div className="flex flex-wrap items-center gap-2 px-4 py-2">
        <select aria-label="Filter by token kind" className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">All kinds ({data.token_count})</option>
          {Object.entries(data.kind_counts).map(([k, n]) => <option key={k} value={k}>{k} ({n})</option>)}
        </select>
        <input aria-label="Search tokens" className="input w-44" placeholder="Search token text…"
          value={query} onChange={(e) => setQuery(e.target.value)} />
        <span className="text-xs text-slate-500">
          {rows.length} shown · {data.header_tokens_excluded} header tokens excluded
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
        <table className="data-table">
          <thead><tr><th>#</th><th>Kind</th><th>Text</th><th>Line:Col</th><th>Flags</th></tr></thead>
          <tbody>
            {rows.map((t, i) => (
              <tr key={i} className="cursor-pointer" onClick={() => t.line && onFocusLine(t.line)}>
                <td className="text-slate-600">{i + 1}</td>
                <td className="text-violet-300">{t.kind}</td>
                <td className="font-mono text-slate-100">{t.text}</td>
                <td className="text-slate-400">{t.line}:{t.column}</td>
                <td className="text-slate-500">
                  {t.from_macro && <span className="mr-1 rounded bg-amber-900/50 px-1 text-amber-200">macro</span>}
                  {t.flags.join(' ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
