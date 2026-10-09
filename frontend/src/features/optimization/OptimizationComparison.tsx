import { useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'
import type { FunctionDiff, OptimizationResponse, OptLevel, SourceRequest } from '../../types/api'
import { api, ApiError } from '../../services/api'
import { EmptyState, ErrorState, LoadingState, PhaseHeader } from '../../components/common'
import { toSideBySide } from './diffRows'

const LEVELS: OptLevel[] = ['O0', 'O1', 'O2', 'O3', 'Os', 'Oz']

function FunctionDiffView({ diff }: { diff: FunctionDiff }) {
  const [open, setOpen] = useState(diff.status !== 'unchanged')
  const rows = toSideBySide(diff.lines)
  return (
    <div className="rounded border border-slate-800">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 bg-slate-900 px-3 py-1.5 text-left text-xs">
        <span className="text-slate-500">{open ? '▾' : '▸'}</span>
        <span className="font-mono text-slate-100">@{diff.name}</span>
        <span className="rounded bg-slate-800 px-1.5 text-slate-300">{diff.status}</span>
        <span className="ml-auto text-slate-400">{diff.baseline_count} → {diff.optimized_count} instructions</span>
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full table-fixed font-mono text-[11.5px]">
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className={`w-1/2 whitespace-pre px-2 align-top ${r.left !== null && r.kind !== 'equal' ? 'bg-red-950/50 text-red-200' : 'text-slate-400'} ${r.left === null ? 'bg-slate-950' : ''}`}>
                    {r.left !== null && r.kind !== 'equal' ? '- ' : '  '}{r.left ?? ''}
                  </td>
                  <td className={`w-1/2 whitespace-pre border-l border-slate-800 px-2 align-top ${r.right !== null && r.kind !== 'equal' ? 'bg-emerald-950/50 text-emerald-200' : 'text-slate-400'} ${r.right === null ? 'bg-slate-950' : ''}`}>
                    {r.right !== null && r.kind !== 'equal' ? '+ ' : '  '}{r.right ?? ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

interface Props {
  initial: OptimizationResponse
  request: SourceRequest
  availablePasses: Record<string, string>
  explanation: string
}

export function OptimizationComparison({ initial, request, availablePasses, explanation }: Props) {
  const [data, setData] = useState(initial)
  const [mode, setMode] = useState<'levels' | 'passes'>('levels')
  const [baseline, setBaseline] = useState<OptLevel>('O0')
  const [optimized, setOptimized] = useState<OptLevel>('O2')
  const [passes, setPasses] = useState<string[]>([])
  const [view, setView] = useState<'functions' | 'raw' | 'opcodes'>('functions')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      setData(await api.optimization({
        ...request, baseline_level: baseline, optimized_level: optimized,
        passes: mode === 'passes' ? passes : [],
      }))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const passNames = Object.keys(availablePasses)
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-4 py-2 text-xs">
        <div className="flex overflow-hidden rounded border border-slate-700">
          <button type="button" className={`px-2 py-1 ${mode === 'levels' ? 'bg-slate-700 text-white' : 'text-slate-400'}`} onClick={() => setMode('levels')}>Compare levels</button>
          <button type="button" disabled={!passNames.length} title={!passNames.length ? 'LLVM opt not available' : undefined}
            className={`px-2 py-1 disabled:opacity-40 ${mode === 'passes' ? 'bg-slate-700 text-white' : 'text-slate-400'}`} onClick={() => setMode('passes')}>Run passes</button>
        </div>
        {mode === 'levels' ? (
          <>
            <select aria-label="Baseline level" className="input" value={baseline} onChange={(e) => setBaseline(e.target.value as OptLevel)}>
              {LEVELS.map((l) => <option key={l} value={l}>-{l}</option>)}
            </select>
            <span className="text-slate-500">vs</span>
            <select aria-label="Optimized level" className="input" value={optimized} onChange={(e) => setOptimized(e.target.value as OptLevel)}>
              {LEVELS.map((l) => <option key={l} value={l}>-{l}</option>)}
            </select>
          </>
        ) : (
          <div className="flex flex-wrap items-center gap-1">
            <select aria-label="Add pass" className="input" value="" onChange={(e) => e.target.value && setPasses([...passes, e.target.value])}>
              <option value="">+ add pass…</option>
              {passNames.map((p) => <option key={p} value={p} title={availablePasses[p]}>{p}</option>)}
            </select>
            {passes.map((p, i) => (
              <button key={i} type="button" className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-slate-200"
                onClick={() => setPasses(passes.filter((_, j) => j !== i))} title="Remove">
                {p} ×
              </button>
            ))}
          </div>
        )}
        <button type="button" className="btn-primary" disabled={busy || (mode === 'passes' && !passes.length)} onClick={run}>
          {busy ? 'Running…' : 'Run comparison'}
        </button>
      </div>
      {busy && <LoadingState label="Compiling both versions…" />}
      {error && <ErrorState message={error} />}
      {!busy && (
        <div className="min-h-0 flex-1 overflow-auto">
          <PhaseHeader result={data} explanation={explanation} />
          {data.status === 'success' && (
            <div className="space-y-4 p-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="stat"><div className="stat-label">{data.baseline_label}</div><div className="stat-value">{data.baseline_count}</div><div className="stat-sub">IR instructions</div></div>
                <div className="stat"><div className="stat-label">{data.optimized_label}</div><div className="stat-value">{data.optimized_count}</div><div className="stat-sub">IR instructions</div></div>
                <div className="stat"><div className="stat-label">Change</div><div className="stat-value">{data.optimized_count - data.baseline_count >= 0 ? '+' : ''}{data.optimized_count - data.baseline_count}</div><div className="stat-sub">static count, not speed</div></div>
              </div>
              <section>
                <h3 className="section-title">Observed changes</h3>
                <p className="mb-2 text-xs text-slate-500">Derived from comparing the two outputs. “Consistent with” means the evidence fits a known transformation; it is not a claim about which pass did it.</p>
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
                  {data.observations.map((o) => <li key={o}>{o}</li>)}
                </ul>
              </section>
              <section>
                <h3 className="section-title">Passes that changed the IR</h3>
                <p className="mb-2 text-xs text-slate-500">{data.pass_timeline_note}</p>
                {data.pass_timeline.length > 0 && (
                  <ol className="flex flex-wrap gap-1.5 text-[11px]">
                    {data.pass_timeline.map((p, i) => (
                      <li key={i} className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5">
                        <span className="text-slate-500">{i + 1}.</span> <span className="text-sky-300">{p.pass_name.replace(/Pass$/, '')}</span>{' '}
                        <span className="text-slate-500">on {p.scope}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
              <div className="flex overflow-hidden rounded border border-slate-700 text-xs" style={{ width: 'fit-content' }}>
                {(['functions', 'opcodes', 'raw'] as const).map((v) => (
                  <button key={v} type="button" onClick={() => setView(v)} className={`px-2 py-1 ${view === v ? 'bg-slate-700 text-white' : 'text-slate-400'}`}>
                    {v === 'functions' ? 'Instruction diff' : v === 'opcodes' ? 'Opcode counts' : 'Raw before/after'}
                  </button>
                ))}
              </div>
              {view === 'functions' && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-500">Lines are matched after normalizing SSA names and metadata. Red = only in {data.baseline_label}, green = only in {data.optimized_label}.</p>
                  {data.function_diffs.length ? data.function_diffs.map((d) => <FunctionDiffView key={d.name} diff={d} />)
                    : <EmptyState>No function definitions to compare.</EmptyState>}
                </div>
              )}
              {view === 'opcodes' && (
                <table className="data-table max-w-md">
                  <thead><tr><th>Opcode</th><th>{data.baseline_label}</th><th>{data.optimized_label}</th><th>Δ</th></tr></thead>
                  <tbody>{Object.entries(data.opcode_delta).sort((a, b) => (b[1][0] + b[1][1]) - (a[1][0] + a[1][1])).map(([op, [a, b]]) => (
                    <tr key={op}><td className="font-mono">{op}</td><td>{a}</td><td>{b}</td>
                      <td className={b < a ? 'text-emerald-300' : b > a ? 'text-amber-300' : 'text-slate-500'}>{b - a > 0 ? '+' : ''}{b - a}</td></tr>
                  ))}</tbody>
                </table>
              )}
              {view === 'raw' && (
                <div className="h-[480px] rounded border border-slate-800">
                  {/* keepCurrent*Model avoids Monaco's "TextModel got disposed before
                      DiffEditorWidget model got reset" error when this view unmounts. */}
                  <DiffEditor original={data.baseline_ir} modified={data.optimized_ir} language="llvm-ir" theme="vs-dark"
                    keepCurrentOriginalModel keepCurrentModifiedModel
                    options={{ readOnly: true, minimap: { enabled: false }, fontSize: 12, renderSideBySide: true, automaticLayout: true }} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
