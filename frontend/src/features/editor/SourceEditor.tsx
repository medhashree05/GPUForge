import { useEffect, useRef } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'
import type { Language, OptLevel, Sample, Target, ToolchainInfo } from '../../types/api'

export interface EditorSettings {
  language: Language
  optLevel: OptLevel
  target: Target
  gpuArch: string
}

interface Props {
  source: string
  settings: EditorSettings
  samples: Sample[]
  toolchain: ToolchainInfo | null
  busy: boolean
  /** Source line to reveal/highlight (from diagnostics, tokens, AST, assembly). */
  focusLine: number | null
  onSourceChange: (s: string) => void
  onSettingsChange: (s: EditorSettings) => void
  onLoadSample: (s: Sample) => void
  onCompile: () => void
  onReset: () => void
  onClear: () => void
}

const OPT_LEVELS: OptLevel[] = ['O0', 'O1', 'O2', 'O3', 'Os', 'Oz']
const MONACO_LANG: Record<Language, string> = { c: 'c', cpp: 'cpp', cuda: 'cpp' }
type MonacoEditor = Parameters<OnMount>[0]

export function SourceEditor(p: Props) {
  const { settings, toolchain } = p
  const editorRef = useRef<MonacoEditor | null>(null)
  const deco = useRef<string[]>([])
  const ptxAvailable = toolchain?.capabilities.ptx ?? false
  const tooLarge = new Blob([p.source]).size > 64 * 1024
  const set = (patch: Partial<EditorSettings>) => p.onSettingsChange({ ...settings, ...patch })

  useEffect(() => {
    const ed = editorRef.current
    if (!ed) return
    deco.current = ed.deltaDecorations(deco.current, p.focusLine ? [{
      range: { startLineNumber: p.focusLine, startColumn: 1, endLineNumber: p.focusLine, endColumn: 1 },
      options: { isWholeLine: true, className: 'mapped-line' },
    }] : [])
    if (p.focusLine) ed.revealLineInCenterIfOutsideViewport(p.focusLine)
  }, [p.focusLine])

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Source editor">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-3 py-2">
        <select
          aria-label="Sample program"
          className="input max-w-56"
          value=""
          onChange={(e) => {
            const s = p.samples.find((x) => x.id === e.target.value)
            if (s) p.onLoadSample(s)
          }}
        >
          <option value="">Load sample…</option>
          {p.samples.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        <select aria-label="Language" className="input" value={settings.language}
          onChange={(e) => {
            const language = e.target.value as Language
            set({ language, target: language === 'cuda' ? 'ptx' : 'cpu' })
          }}>
          <option value="c">C</option>
          <option value="cpp">C++</option>
          <option value="cuda">CUDA</option>
        </select>
        <label className="flex items-center gap-1 text-xs text-slate-400">
          Opt
          <select aria-label="Optimization level" className="input" value={settings.optLevel}
            onChange={(e) => set({ optLevel: e.target.value as OptLevel })}>
            {OPT_LEVELS.map((o) => <option key={o} value={o}>-{o}</option>)}
          </select>
        </label>
        <div role="radiogroup" aria-label="Target" className="flex overflow-hidden rounded border border-slate-700 text-xs">
          {(['cpu', 'ptx'] as Target[]).map((t) => (
            <button key={t} type="button" role="radio" aria-checked={settings.target === t}
              disabled={t === 'ptx' && !ptxAvailable}
              title={t === 'ptx' && !ptxAvailable ? 'No PTX toolchain detected' : undefined}
              className={`px-2 py-1 ${settings.target === t ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'} disabled:opacity-40`}
              onClick={() => set({ target: t })}>
              {t === 'cpu' ? `CPU${toolchain?.host_arch ? ` (${toolchain.host_arch})` : ''}` : 'NVIDIA PTX'}
            </button>
          ))}
        </div>
        {settings.target === 'ptx' && (
          <select aria-label="GPU architecture" className="input" value={settings.gpuArch}
            onChange={(e) => set({ gpuArch: e.target.value })}>
            {(toolchain?.allowed_gpu_archs ?? ['sm_75']).map((a) => <option key={a}>{a}</option>)}
          </select>
        )}
        <div className="ml-auto flex gap-2">
          <button type="button" className="btn-ghost" onClick={p.onReset}>Reset</button>
          <button type="button" className="btn-ghost" onClick={p.onClear}>Clear</button>
          <button
            type="button" className="btn-primary" onClick={p.onCompile}
            disabled={p.busy || !p.source.trim() || tooLarge || !toolchain?.clang.available}
          >
            {p.busy ? 'Compiling…' : 'Compile & Analyze'}
          </button>
        </div>
      </div>
      {settings.target === 'ptx' && settings.language !== 'cuda' && (
        <div className="border-b border-slate-800 bg-amber-950/30 px-3 py-1 text-xs text-amber-200/90">
          PTX target needs CUDA source: switch the language to CUDA (or load the CUDA sample).
        </div>
      )}
      {tooLarge && (
        <div className="border-b border-slate-800 bg-red-950/40 px-3 py-1 text-xs text-red-200">
          Source exceeds the 64 KiB limit.
        </div>
      )}
      <div className="min-h-0 flex-1">
        <Editor
          value={p.source}
          language={MONACO_LANG[settings.language]}
          theme="vs-dark"
          onChange={(v) => p.onSourceChange(v ?? '')}
          onMount={(ed) => { editorRef.current = ed }}
          options={{ minimap: { enabled: false }, fontSize: 13.5, scrollBeyondLastLine: false, automaticLayout: true, tabSize: 4 }}
        />
      </div>
    </section>
  )
}
