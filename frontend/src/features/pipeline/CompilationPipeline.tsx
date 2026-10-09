import { useMemo } from 'react'
import { Background, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { PHASES, STATUS_STYLE, phaseStatus, type PhaseId } from '../../lib/phases'
import type { FullAnalysis, PhaseStatus } from '../../types/api'

type PhaseNodeData = { label: string; status: PhaseStatus | 'idle'; selected: boolean; toolOk: boolean }

function PhaseNode({ data }: NodeProps<Node<PhaseNodeData>>) {
  const s = STATUS_STYLE[data.status]
  return (
    <div
      className={`flex w-44 items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs ${
        data.selected ? 'border-sky-400 bg-sky-950/60' : 'border-slate-700 bg-slate-900'
      } ${data.toolOk ? '' : 'opacity-50'}`}
      title={`${data.label}: ${s.label}${data.toolOk ? '' : ' (toolchain unavailable)'}`}
    >
      <Handle type="target" position={Position.Top} className="!h-1 !w-1 !border-0 !bg-slate-600" />
      <span className={`h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
      <span className="truncate text-slate-200">{data.label}</span>
      <span className={`ml-auto text-[10px] ${s.text}`}>{s.label}</span>
      <Handle type="source" position={Position.Bottom} className="!h-1 !w-1 !border-0 !bg-slate-600" />
    </div>
  )
}

const nodeTypes = { phase: PhaseNode }

interface Props {
  result: FullAnalysis | null
  selected: PhaseId
  capabilities: Record<string, boolean> | undefined
  onSelect: (id: PhaseId) => void
}

/** Vertical React Flow diagram: Source → Tokens → … → Report. Click a node to open the phase. */
export function CompilationPipeline({ result, selected, capabilities, onSelect }: Props) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node<PhaseNodeData>[] = PHASES.map((p, i) => ({
      id: p.id,
      type: 'phase',
      position: { x: 0, y: i * 46 },
      data: {
        label: p.label,
        status: phaseStatus(p.id, result),
        selected: p.id === selected,
        toolOk: p.id === 'source' || p.id === 'metrics' || (capabilities?.[p.id] ?? true),
      },
      draggable: false,
      connectable: false,
    }))
    const edges: Edge[] = PHASES.slice(1).map((p, i) => {
      const st = phaseStatus(p.id, result)
      return {
        id: `${PHASES[i].id}-${p.id}`, source: PHASES[i].id, target: p.id,
        animated: st === 'success',
        style: { stroke: st === 'failed' ? '#f87171' : st === 'success' ? '#34d399' : '#475569' },
      }
    })
    return { nodes, edges }
  }, [result, selected, capabilities])

  return (
    <div className="h-[430px] w-full" aria-label="Compilation pipeline">
      <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        fitView fitViewOptions={{ padding: 0.08 }}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}
        panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false}
        preventScrolling={false} proOptions={{ hideAttribution: true }}
        onNodeClick={(_, n) => onSelect(n.id as PhaseId)}
      >
        <Background color="#1e293b" gap={16} />
      </ReactFlow>
    </div>
  )
}
