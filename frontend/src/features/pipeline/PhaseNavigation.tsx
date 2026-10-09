import { PHASES, STATUS_STYLE, phaseStatus, type PhaseId } from '../../lib/phases'
import type { FullAnalysis } from '../../types/api'

interface Props {
  result: FullAnalysis | null
  selected: PhaseId
  onSelect: (id: PhaseId) => void
}

/** Tab strip over the output panel (the sidebar diagram selects the same phases). */
export function PhaseNavigation({ result, selected, onSelect }: Props) {
  return (
    <div role="tablist" aria-label="Compilation phases" className="flex overflow-x-auto border-b border-slate-800">
      {PHASES.filter((p) => p.id !== 'source').map((p) => {
        const st = STATUS_STYLE[phaseStatus(p.id, result)]
        const active = p.id === selected
        return (
          <button
            key={p.id} role="tab" type="button" aria-selected={active}
            onClick={() => onSelect(p.id)}
            className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-xs ${
              active ? 'border-sky-400 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
            {p.short}
          </button>
        )
      })}
    </div>
  )
}
