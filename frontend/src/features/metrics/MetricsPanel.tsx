import type { FullAnalysis } from '../../types/api'
import { StatusBadge } from '../../components/common'
import { PHASES } from '../../lib/phases'

export function MetricsPanel({ result }: { result: FullAnalysis }) {
  const metrics = result.metrics.metrics
  return (
    <div className="h-full overflow-auto p-4">
      <h3 className="section-title">Phase summary</h3>
      <div className="mb-5 grid gap-2 sm:grid-cols-2">
        {PHASES.filter((p) => p.id !== 'source' && p.id !== 'metrics').map((p) => {
          const r = result[p.id as Exclude<typeof p.id, 'source' | 'metrics'>]
          return (
            <div key={p.id} className="rounded border border-slate-800 p-2 text-xs">
              <div className="flex items-center justify-between"><span className="text-slate-200">{p.label}</span><StatusBadge status={r.status} /></div>
              <div className="mt-1 text-slate-500">{r.message}</div>
            </div>
          )
        })}
      </div>
      <h3 className="section-title">Metrics</h3>
      <table className="data-table">
        <thead><tr><th>Metric</th><th>Value</th><th>Definition and limitations</th></tr></thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.key}>
              <td className="whitespace-nowrap text-slate-200">{m.label}</td>
              <td className="whitespace-nowrap font-mono">
                {m.value === null ? <span className="text-slate-500">Unavailable</span> : `${m.value}${m.unit ? ` ${m.unit}` : ''}`}
              </td>
              <td className="text-slate-400">
                {m.definition}
                {m.limitation && <div className="text-slate-500">Limitation: {m.limitation}</div>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
