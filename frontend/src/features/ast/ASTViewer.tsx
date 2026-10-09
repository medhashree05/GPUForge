import { useMemo, useState } from 'react'
import type { ASTNode, ASTResponse } from '../../types/api'
import { CodeView } from '../../components/CodeView'
import { EmptyState, PhaseHeader } from '../../components/common'

function matches(n: ASTNode, q: string): boolean {
  return n.kind.toLowerCase().includes(q) || n.children.some((c) => matches(c, q))
}

function TreeNode({ node, depth, query, expandAll, onFocusLine }: {
  node: ASTNode; depth: number; query: string; expandAll: boolean | null; onFocusLine: (l: number) => void
}) {
  const [open, setOpen] = useState(depth < 2)
  const isOpen = expandAll ?? (query ? true : open)
  if (query && !matches(node, query)) return null
  const hit = query && node.kind.toLowerCase().includes(query)
  return (
    <li>
      <div
        className={`flex cursor-pointer items-baseline gap-1.5 rounded px-1 py-0.5 hover:bg-slate-800/70 ${hit ? 'bg-sky-950/60' : ''}`}
        style={{ paddingLeft: depth * 14 }}
        onClick={() => { setOpen(!isOpen); if (node.line) onFocusLine(node.line) }}
      >
        <span className="w-3 text-slate-500">{node.children.length ? (isOpen ? '▾' : '▸') : ''}</span>
        <span className={`font-mono ${node.implicit ? 'text-slate-500' : 'text-emerald-300'}`}>{node.kind}</span>
        {node.name && <span className="text-slate-100">{node.name}</span>}
        {node.detail && <span className="text-amber-200/80">{node.detail}</span>}
        {node.type && <span className="text-sky-300/80">'{node.type}'</span>}
        {node.line && <span className="text-[10px] text-slate-600">line {node.line}</span>}
      </div>
      {isOpen && node.children.length > 0 && (
        <ul>
          {node.children.map((c) => (
            <TreeNode key={c.id + c.kind} node={c} depth={depth + 1} query={query} expandAll={expandAll} onFocusLine={onFocusLine} />
          ))}
        </ul>
      )}
    </li>
  )
}

export function ASTViewer({ data, onFocusLine, explanation }: {
  data: ASTResponse; onFocusLine: (l: number) => void; explanation: string
}) {
  const [view, setView] = useState<'tree' | 'raw'>('tree')
  const [query, setQuery] = useState('')
  const [expandAll, setExpandAll] = useState<boolean | null>(null)
  const kinds = useMemo(() => Object.keys(data.kind_counts).sort(), [data.kind_counts])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PhaseHeader result={data} explanation={explanation} />
      <div className="flex flex-wrap items-center gap-2 px-4 py-2">
        <div className="flex overflow-hidden rounded border border-slate-700 text-xs">
          {(['tree', 'raw'] as const).map((v) => (
            <button key={v} type="button" onClick={() => setView(v)}
              className={`px-2 py-1 ${view === v ? 'bg-slate-700 text-white' : 'text-slate-400'}`}>
              {v === 'tree' ? 'Tree' : 'Raw clang -ast-dump'}
            </button>
          ))}
        </div>
        {view === 'tree' && (
          <>
            <input list="ast-kinds" aria-label="Search node type" className="input w-48" placeholder="Search node type…"
              value={query} onChange={(e) => setQuery(e.target.value.toLowerCase())} />
            <datalist id="ast-kinds">{kinds.map((k) => <option key={k} value={k} />)}</datalist>
            <button type="button" className="btn-ghost" onClick={() => setExpandAll(true)}>Expand all</button>
            <button type="button" className="btn-ghost" onClick={() => setExpandAll(false)}>Collapse all</button>
            {expandAll !== null && <button type="button" className="btn-ghost" onClick={() => setExpandAll(null)}>Manual</button>}
          </>
        )}
        <span className="ml-auto text-xs text-slate-500">
          {data.node_count} nodes · {data.header_decls_excluded} header/implicit top-level decls hidden
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-3 pb-4 text-xs">
        {view === 'raw' ? (
          <div className="h-full min-h-[300px]"><CodeView value={data.raw_text} language="plaintext" /></div>
        ) : data.nodes.length ? (
          <ul>{data.nodes.map((n) => (
            <TreeNode key={n.id} node={n} depth={0} query={query} expandAll={expandAll} onFocusLine={onFocusLine} />
          ))}</ul>
        ) : <EmptyState>No AST nodes from your file.</EmptyState>}
      </div>
    </div>
  )
}
