import type { ToolchainInfo, ToolStatus } from '../../types/api'

function Tool({ t, optional }: { t: ToolStatus; optional?: string }) {
  return (
    <div className="rounded border border-slate-800 p-2 text-xs">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${t.available ? 'bg-emerald-400' : optional ? 'bg-slate-500' : 'bg-red-400'}`} />
        <span className="font-mono text-slate-100">{t.name}</span>
        <span className="text-slate-500">{t.available ? 'available' : optional ? `not found (${optional})` : 'not found'}</span>
      </div>
      {t.version && <div className="mt-1 text-slate-400">{t.version}</div>}
      {t.path && <div className="truncate font-mono text-[10.5px] text-slate-600" title={t.path}>{t.path}</div>}
      {!t.available && t.error && <div className="mt-1 text-slate-500">{t.error}</div>}
    </div>
  )
}

export function SettingsPanel({ toolchain, onRefresh, onClose }: {
  toolchain: ToolchainInfo | null; onRefresh: () => void; onClose: () => void
}) {
  return (
    <div role="dialog" aria-label="Toolchain settings" className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4" onClick={onClose}>
      <div className="mt-12 w-full max-w-xl space-y-3 rounded-lg border border-slate-700 bg-slate-900 p-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center">
          <h2 className="text-sm font-semibold text-slate-100">Toolchain</h2>
          <button type="button" className="btn-ghost ml-auto" onClick={onRefresh}>Re-detect</button>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {!toolchain ? <div className="text-sm text-slate-400">Toolchain information unavailable.</div> : (
          <>
            <Tool t={toolchain.clang} />
            <Tool t={toolchain.opt} optional="pass experiments disabled" />
            <Tool t={toolchain.nvcc} optional="Clang NVPTX used if available" />
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
              <div>Host target: <span className="font-mono text-slate-200">{toolchain.host_triple ?? 'unknown'}</span></div>
              <div>Standard headers: <span className="text-slate-200">{toolchain.system_headers ? 'found' : 'missing'}</span></div>
              <div>NVPTX backend: <span className="text-slate-200">{toolchain.nvptx_backend ? 'yes' : 'no'}</span></div>
              <div>PTX method: <span className="text-slate-200">{toolchain.ptx_method ?? 'none'}</span></div>
            </div>
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              {Object.entries(toolchain.capabilities).map(([k, v]) => (
                <span key={k} className={`rounded px-1.5 py-0.5 ${v ? 'bg-emerald-950 text-emerald-300' : 'bg-slate-800 text-slate-500'}`}>{k}</span>
              ))}
            </div>
            {toolchain.notes.map((n) => <p key={n} className="text-xs text-amber-200/80">{n}</p>)}
            <p className="text-[11px] text-slate-500">
              Configure paths in <code>backend/.env</code> (GPUFORGE_LLVM_BIN_DIR, GPUFORGE_NVCC_PATH), then Re-detect.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
