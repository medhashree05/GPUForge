import type { IRResponse } from '../../types/api'
import { CodeView } from '../../components/CodeView'
import { CountBars, Explanations, PhaseHeader } from '../../components/common'

export function IRViewer({ data, explanation }: { data: IRResponse; explanation: string }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      {data.status === 'success' && (
        <div className="grid min-h-0 flex-1 grid-rows-[minmax(260px,1fr)_auto] overflow-auto lg:grid-cols-[1fr_300px] lg:grid-rows-1">
          <div className="min-h-[260px]">
            <CodeView value={data.ir} language="llvm-ir"
              toolbar={<span className="text-xs text-slate-500">-{data.opt_level} · {data.target_triple}</span>} />
          </div>
          <aside className="space-y-3 overflow-auto border-t border-slate-800 lg:border-l lg:border-t-0">
            <div className="p-4 pb-0">
              <h3 className="section-title">Functions</h3>
              <table className="data-table">
                <thead><tr><th>Name</th><th>Instr.</th><th>Blocks</th></tr></thead>
                <tbody>{data.functions.map((f) => (
                  <tr key={f.name}>
                    <td className="max-w-40 truncate font-mono" title={f.name}>{f.name}{f.is_declaration && <span className="text-slate-500"> (decl)</span>}</td>
                    <td>{f.is_declaration ? '-' : f.instruction_count}</td>
                    <td>{f.is_declaration ? '-' : f.block_count}</td>
                  </tr>
                ))}</tbody>
              </table>
              <h3 className="section-title mt-3">Opcodes ({data.instruction_count})</h3>
              <CountBars counts={data.opcode_counts} />
            </div>
            <Explanations items={data.explanations} title="Instructions in this IR" />
          </aside>
        </div>
      )}
    </div>
  )
}
