import { useCallback, useEffect, useState } from 'react'
import { SourceEditor, type EditorSettings } from './features/editor/SourceEditor'
import { CompilationPipeline } from './features/pipeline/CompilationPipeline'
import { PhaseNavigation } from './features/pipeline/PhaseNavigation'
import { TokenViewer } from './features/tokens/TokenViewer'
import { ASTViewer } from './features/ast/ASTViewer'
import { DiagnosticsPanel } from './features/diagnostics/DiagnosticsPanel'
import { IRViewer } from './features/ir/IRViewer'
import { OptimizationComparison } from './features/optimization/OptimizationComparison'
import { AssemblyViewer } from './features/assembly/AssemblyViewer'
import { PTXViewer } from './features/ptx/PTXViewer'
import { MetricsPanel } from './features/metrics/MetricsPanel'
import { SettingsPanel } from './features/settings/SettingsPanel'
import { CompilationHistory, type HistoryEntry } from './features/history/CompilationHistory'
import { EmptyState, ErrorState, LoadingState } from './components/common'
import { useAnalysis, useToolchain } from './hooks/useBackend'
import { PHASES, type PhaseId } from './lib/phases'
import type { Sample, SourceRequest } from './types/api'

const DEFAULT_SOURCE = `int main(void) {
    int x = 10 + 20;
    return x;
}
`
const DEFAULT_SETTINGS: EditorSettings = { language: 'c', optLevel: 'O0', target: 'cpu', gpuArch: 'sm_75' }
let nextId = 1

export default function App() {
  const { toolchain, samples, error: backendError, reload } = useToolchain()
  const { result, setResult, loading, error, run } = useAnalysis()
  const [source, setSource] = useState(DEFAULT_SOURCE)
  const [settings, setSettings] = useState<EditorSettings>(DEFAULT_SETTINGS)
  const [phase, setPhase] = useState<PhaseId>('source')
  const [focusLine, setFocusLine] = useState<number | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [activeRun, setActiveRun] = useState<HistoryEntry | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const toRequest = useCallback((): SourceRequest => ({
    source, language: settings.language, opt_level: settings.optLevel, target: settings.target, gpu_arch: settings.gpuArch,
  }), [source, settings])

  const compile = useCallback(async () => {
    const req = toRequest()
    const r = await run(req)
    if (!r) return
    const entry: HistoryEntry = { id: nextId++, time: new Date().toLocaleTimeString(), request: req, result: r }
    setHistory((h) => [entry, ...h].slice(0, 20))
    setActiveRun(entry)
    setFocusLine(null)
    if (phase === 'source') {
      setPhase(r.diagnostics.status === 'failed' ? 'diagnostics' : req.target === 'ptx' ? 'ptx' : 'tokens')
    }
  }, [toRequest, run, phase])

  // Ctrl/Cmd+Enter compiles.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !loading) { e.preventDefault(); void compile() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [compile, loading])

  const loadSample = (s: Sample) => {
    setSource(s.source)
    setSettings({ ...settings, language: s.language, target: s.language === 'cuda' ? 'ptx' : 'cpu' })
  }

  const restore = (e: HistoryEntry) => {
    setSource(e.request.source)
    setSettings({ language: e.request.language, optLevel: e.request.opt_level, target: e.request.target, gpuArch: e.request.gpu_arch })
    setResult(e.result)
    setActiveRun(e)
  }

  const info = PHASES.find((p) => p.id === phase)!
  const req = activeRun?.request
  const stale = !!req && (req.source !== source || req.language !== settings.language || req.opt_level !== settings.optLevel || req.gpu_arch !== settings.gpuArch)

  const renderPhase = () => {
    if (loading) return <LoadingState label="Running Clang on every phase…" />
    if (error) return <ErrorState title="Analysis failed" message={error} onRetry={compile} />
    if (phase === 'source' || !result || !req) {
      return <EmptyState><p className="mb-2 text-slate-300">{info.explanation}</p>Write or load a program, then press <b>Compile &amp; Analyze</b> (Ctrl+Enter).</EmptyState>
    }
    const key = activeRun!.id
    switch (phase) {
      case 'tokens': return <TokenViewer data={result.tokens} onFocusLine={setFocusLine} explanation={info.explanation} />
      case 'ast': return <ASTViewer data={result.ast} onFocusLine={setFocusLine} explanation={info.explanation} />
      case 'diagnostics': return <DiagnosticsPanel data={result.diagnostics} onFocusLine={setFocusLine} explanation={info.explanation} />
      case 'ir': return <IRViewer data={result.ir} explanation={info.explanation} />
      case 'optimization': return result.optimization.status === 'success'
        ? <OptimizationComparison key={key} initial={result.optimization} request={req} availablePasses={toolchain?.allowed_passes ?? {}} explanation={info.explanation} />
        : <IRLikeStatus r={result.optimization} explanation={info.explanation} />
      case 'assembly': return <AssemblyViewer data={result.assembly} focusLine={focusLine} onFocusLine={setFocusLine} explanation={info.explanation} />
      case 'ptx': return <PTXViewer key={key} initial={result.ptx} request={req} toolchain={toolchain} explanation={info.explanation} />
      case 'metrics': return <MetricsPanel result={result} />
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-200">
      <header className="flex items-center gap-3 border-b border-slate-800 px-4 py-2">
        <div className="font-semibold tracking-tight text-white">GPU<span className="text-sky-400">Forge</span></div>
        <div className="hidden text-xs text-slate-500 sm:block">Compiler pipeline visualization &amp; optimization analyzer</div>
        <div className="ml-auto flex items-center gap-3 text-xs">
          {toolchain && (
            <>
              <ToolDot ok={toolchain.clang.available} label={toolchain.clang.version?.match(/clang version [\d.]+/)?.[0] ?? 'clang'} />
              <ToolDot ok={toolchain.opt.available} label="opt" />
              <ToolDot ok={toolchain.ptx_method !== null} label={`PTX${toolchain.ptx_method ? ` (${toolchain.ptx_method})` : ''}`} />
            </>
          )}
          <button type="button" className="btn-ghost" onClick={() => setSettingsOpen(true)}>Toolchain</button>
        </div>
      </header>
      {backendError && <ErrorState title="Backend unavailable" message={backendError} onRetry={() => reload()} />}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside className="flex shrink-0 flex-col gap-2 overflow-y-auto border-b border-slate-800 py-3 lg:w-60 lg:border-b-0 lg:border-r">
          <h2 className="section-title px-3">Pipeline</h2>
          <div className="px-2"><CompilationPipeline result={result} selected={phase} capabilities={toolchain?.capabilities} onSelect={setPhase} /></div>
          <p className="px-3 text-[11px] leading-relaxed text-slate-500">An educational view of the workflow. Clang interleaves some of these steps internally.</p>
          <h2 className="section-title mt-2 px-3">History</h2>
          <CompilationHistory entries={history} activeId={activeRun?.id ?? null} onRestore={restore} />
        </aside>
        <main className="grid min-h-0 flex-1 grid-rows-[minmax(280px,42%)_1fr] xl:grid-cols-[minmax(380px,40%)_1fr] xl:grid-rows-1">
          <div className="min-h-0 border-b border-slate-800 xl:border-b-0 xl:border-r">
            <SourceEditor
              source={source} settings={settings} samples={samples} toolchain={toolchain} busy={loading}
              focusLine={focusLine} onSourceChange={setSource} onSettingsChange={setSettings}
              onLoadSample={loadSample} onCompile={compile}
              onReset={() => { setSource(DEFAULT_SOURCE); setSettings(DEFAULT_SETTINGS) }}
              onClear={() => setSource('')}
            />
          </div>
          <section className="flex min-h-0 flex-col" aria-label="Phase output">
            <PhaseNavigation result={result} selected={phase} onSelect={setPhase} />
            {stale && result && !loading && (
              <div className="border-b border-slate-800 bg-sky-950/40 px-4 py-1 text-xs text-sky-200">
                Source or settings changed since this run; outputs below are for the previous compile. Press Compile &amp; Analyze to refresh.
              </div>
            )}
            <div className="min-h-0 flex-1">{renderPhase()}</div>
          </section>
        </main>
      </div>
      {settingsOpen && <SettingsPanel toolchain={toolchain} onRefresh={() => reload(true)} onClose={() => setSettingsOpen(false)} />}
    </div>
  )
}

function ToolDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="hidden items-center gap-1 text-slate-400 md:flex">
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-emerald-400' : 'bg-slate-600'}`} />{label}
    </span>
  )
}

function IRLikeStatus({ r, explanation }: { r: { status: string; message: string }; explanation: string }) {
  return <EmptyState><p className="mb-2">{explanation}</p><b className="text-slate-300">{r.status}:</b> {r.message}</EmptyState>
}
