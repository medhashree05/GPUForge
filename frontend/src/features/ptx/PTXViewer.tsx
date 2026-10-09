import { useState } from 'react'
import type { OptLevel, PTXResponse, PTXSummary, SourceRequest, ToolchainInfo } from '../../types/api'
import { api, ApiError } from '../../services/api'
import { CodeView } from '../../components/CodeView'
import { CountBars, ErrorState, Explanations, LoadingState, PhaseHeader } from '../../components/common'

function SummaryTable({ a, b }: { a: PTXSummary; b: PTXSummary | null }) {
  const cols = b ? [a, b] : [a]
  const classes = [...new Set(cols.flatMap((c) => Object.keys(c.class_counts)))]
  const spaces = [...new Set(cols.flatMap((c) => Object.keys(c.memory_ops)))]
  return (
    <table className="data-table">
      <thead><tr><th>Static count</th>{cols.map((c) => <th key={c.opt_level}>-{c.opt_level}</th>)}</tr></thead>
      <tbody>
        <tr className="font-semibold"><td>instructions</td>{cols.map((c) => <td key={c.opt_level}>{c.instruction_count}</td>)}</tr>
        <tr><td>branches (bra)</td>{cols.map((c) => <td key={c.opt_level}>{c.branch_count}</td>)}</tr>
        {classes.map((k) => <tr key={k}><td>{k}</td>{cols.map((c) => <td key={c.opt_level}>{c.class_counts[k] ?? 0}</td>)}</tr>)}
        {spaces.map((s) => <tr key={s}><td>memory: {s}</td>{cols.map((c) => <td key={c.opt_level}>{c.memory_ops[s] ?? 0}</td>)}</tr>)}
      </tbody>
    </table>
  )
}

export function PTXViewer({ initial, request, toolchain, explanation }: {
  initial: PTXResponse; request: SourceRequest; toolchain: ToolchainInfo | null; explanation: string
}) {
  const [data, setData] = useState(initial)
  const [cmp, setCmp] = useState<OptLevel>(request.opt_level === 'O0' ? 'O2' : 'O0')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const compare = async () => {
    setBusy(true); setError(null)
    try { setData(await api.ptx({ ...request, compare_opt_level: cmp })) }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)) }
    finally { setBusy(false) }
  }

  if (data.status === 'unsupported') {
    return (
      <div className="h-full overflow-auto">
        <PhaseHeader result={data} explanation={explanation} />
        <div className="space-y-2 p-4 text-sm text-slate-400">
          <p>PTX toolchain: <b className="text-slate-200">{toolchain?.ptx_method ?? 'none detected'}</b>
            {' '}· nvcc: {toolchain?.nvcc.available ? 'found' : 'not found'}
            {' '}· Clang NVPTX backend: {toolchain?.nvptx_backend ? 'available' : 'not available'}</p>
          <p>All CPU-side phases keep working without CUDA. No PTX is shown unless a real compiler produced it.</p>
        </div>
      </div>
    )
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      {data.status === 'success' && (
        <div className="grid min-h-0 flex-1 grid-rows-[minmax(260px,1fr)_auto] overflow-auto lg:grid-cols-[1fr_340px] lg:grid-rows-1">
          <div className="min-h-[260px]">
            <CodeView value={data.ptx} language="ptx"
              toolbar={<span className="text-xs text-slate-500">PTX {data.ptx_version} · {data.target} · {data.method}</span>} />
          </div>
          <aside className="space-y-4 overflow-auto border-t border-slate-800 p-4 lg:border-l lg:border-t-0">
            <section>
              <h3 className="section-title">Kernels & functions</h3>
              {data.functions.map((f) => (
                <div key={f.name} className="mb-2 rounded border border-slate-800 p-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1 ${f.is_kernel ? 'bg-emerald-900/60 text-emerald-200' : 'bg-slate-800 text-slate-300'}`}>{f.is_kernel ? '.entry' : '.func'}</span>
                    <span className="truncate font-mono text-slate-100" title={f.name}>{f.name}</span>
                    <span className="ml-auto text-slate-500">{f.instruction_count} instr.</span>
                  </div>
                  <ul className="mt-1 font-mono text-[10.5px] text-slate-500">{f.params.map((p) => <li key={p}>{p}</li>)}</ul>
                </div>
              ))}
            </section>
            <section>
              <h3 className="section-title">Register declarations</h3>
              <ul className="font-mono text-[11px] text-slate-400">{data.register_decls.map((r) => <li key={r}>{r}</li>)}</ul>
            </section>
            {data.summary && (
              <section>
                <h3 className="section-title">Instruction classes</h3>
                <SummaryTable a={data.summary} b={data.comparison} />
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <span className="text-slate-400">Compare with</span>
                  <select aria-label="PTX comparison level" className="input" value={cmp} onChange={(e) => setCmp(e.target.value as OptLevel)}>
                    {(['O0', 'O1', 'O2', 'O3'] as OptLevel[]).filter((l) => l !== request.opt_level).map((l) => <option key={l} value={l}>-{l}</option>)}
                  </select>
                  <button type="button" className="btn" onClick={compare} disabled={busy}>Compare</button>
                </div>
                {busy && <LoadingState label="Generating PTX…" />}
                {error && <ErrorState message={error} />}
                <h3 className="section-title mt-3">Opcodes</h3>
                <CountBars counts={data.summary.opcode_counts} />
              </section>
            )}
            <Explanations items={data.explanations} title="PTX instructions present" />
          </aside>
        </div>
      )}
    </div>
  )
}
