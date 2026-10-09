import { useMemo, useState } from 'react'
import type { AssemblyResponse } from '../../types/api'
import { CodeView } from '../../components/CodeView'
import { Explanations, PhaseHeader } from '../../components/common'

export function AssemblyViewer({ data, focusLine, onFocusLine, explanation }: {
  data: AssemblyResponse; focusLine: number | null; onFocusLine: (l: number) => void; explanation: string
}) {
  const [raw, setRaw] = useState(false)
  const asmToSrc = useMemo(() => new Map(data.source_map.map((e) => [e.asm_line, e.source_line])), [data.source_map])
  const highlighted = useMemo(
    () => (raw || !focusLine ? [] : data.source_map.filter((e) => e.source_line === focusLine).map((e) => e.asm_line)),
    [raw, focusLine, data.source_map],
  )
  const mnemonics = useMemo(() => {
    const all = new Set(data.comparison.flatMap((v) => Object.keys(v.mnemonic_counts)))
    return [...all].sort((a, b) =>
      Math.max(...data.comparison.map((v) => v.mnemonic_counts[b] ?? 0)) - Math.max(...data.comparison.map((v) => v.mnemonic_counts[a] ?? 0)))
  }, [data.comparison])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      {data.status === 'success' && (
        <div className="grid min-h-0 flex-1 grid-rows-[minmax(260px,1fr)_auto] overflow-auto lg:grid-cols-[1fr_320px] lg:grid-rows-1">
          <div className="min-h-[260px]">
            <CodeView
              value={raw ? data.asm : data.filtered_asm}
              language="target-asm"
              highlightLines={highlighted}
              onLineClick={(ln) => { const s = asmToSrc.get(ln); if (!raw && s) onFocusLine(s) }}
              toolbar={
                <>
                  <span className="text-xs text-slate-500">{data.arch} · -{data.opt_level}</span>
                  <label className="flex items-center gap-1 text-xs text-slate-400">
                    <input type="checkbox" checked={raw} onChange={(e) => setRaw(e.target.checked)} /> raw (with directives)
                  </label>
                </>
              }
            />
          </div>
          <aside className="overflow-auto border-t border-slate-800 lg:border-l lg:border-t-0">
            <div className="space-y-3 p-4">
              <div className="rounded border border-slate-800 bg-slate-900/50 p-2 text-xs text-slate-400">
                Target <span className="font-mono text-slate-200">{data.target_triple}</span>. Assembly is
                architecture-specific; it is not comparable instruction-for-instruction with other targets or PTX.
              </div>
              <div className="text-xs text-slate-400">
                {data.source_map.length
                  ? 'Source mapping: click an instruction to highlight its source line; click a token/diagnostic to highlight the instructions generated for that line.'
                  : 'No source mapping available.'}
              </div>
              <h3 className="section-title">Instruction counts by level</h3>
              <table className="data-table">
                <thead><tr><th>Mnemonic</th>{data.comparison.map((v) => <th key={v.opt_level}>-{v.opt_level}</th>)}</tr></thead>
                <tbody>
                  <tr className="font-semibold"><td>total</td>{data.comparison.map((v) => <td key={v.opt_level}>{v.instruction_count}</td>)}</tr>
                  {mnemonics.slice(0, 20).map((m) => (
                    <tr key={m}><td className="font-mono">{m}</td>{data.comparison.map((v) => <td key={v.opt_level}>{v.mnemonic_counts[m] ?? 0}</td>)}</tr>
                  ))}
                </tbody>
              </table>
              <details className="text-xs text-slate-500">
                <summary className="cursor-pointer">How instructions are counted</summary>
                <p className="mt-1">{data.counting_method}</p>
              </details>
            </div>
            <Explanations items={data.explanations} title="Representative instructions" />
          </aside>
        </div>
      )}
    </div>
  )
}
