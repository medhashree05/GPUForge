import { useEffect, useMemo, useRef, useState } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'
import { CopyButton } from './common'

type MonacoEditor = Parameters<OnMount>[0]

interface Props {
  value: string
  language: string
  height?: string
  /** 1-based line numbers to highlight (e.g. assembly mapped to a source line). */
  highlightLines?: number[]
  onLineClick?: (line: number) => void
  toolbar?: React.ReactNode
}

/** Read-only code viewer: line numbers, highlighting, search and copy. */
export function CodeView({ value, language, height = '100%', highlightLines, onLineClick, toolbar }: Props) {
  // State (not a ref) so the highlight effect re-runs once Monaco has mounted.
  const [editor, setEditor] = useState<MonacoEditor | null>(null)
  const decorations = useRef<string[]>([])
  const [query, setQuery] = useState('')
  const clickRef = useRef(onLineClick)
  clickRef.current = onLineClick

  const matches = useMemo(() => {
    if (!query) return []
    const q = query.toLowerCase()
    return value.split('\n').flatMap((l, i) => (l.toLowerCase().includes(q) ? [i + 1] : []))
  }, [query, value])

  useEffect(() => {
    const ed = editor
    if (!ed) return
    const lines = [...new Set([...(highlightLines ?? []), ...matches])]
    decorations.current = ed.deltaDecorations(decorations.current, lines.map((ln) => ({
      range: { startLineNumber: ln, startColumn: 1, endLineNumber: ln, endColumn: 1 },
      options: {
        isWholeLine: true,
        className: matches.includes(ln) ? 'search-hit-line' : 'mapped-line',
      },
    })))
    const first = highlightLines?.[0] ?? matches[0]
    if (first) ed.revealLineInCenterIfOutsideViewport(first)
  }, [editor, highlightLines, matches])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 px-3 py-1.5">
        <input
          aria-label="Search output"
          className="input w-48"
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && <span className="text-xs text-slate-500">{matches.length} matching line(s)</span>}
        <div className="ml-auto flex items-center gap-2">
          {toolbar}
          <CopyButton text={value} />
        </div>
      </div>
      <div className="min-h-0 flex-1" style={{ height }}>
        <Editor
          value={value}
          language={language}
          theme="vs-dark"
          options={{
            readOnly: true, minimap: { enabled: false }, fontSize: 12.5, scrollBeyondLastLine: false,
            renderLineHighlight: 'none', wordWrap: 'off', automaticLayout: true,
          }}
          onMount={(ed) => {
            setEditor(ed)
            ed.onMouseDown((e) => {
              const ln = e.target.position?.lineNumber
              if (ln && clickRef.current) clickRef.current(ln)
            })
          }}
        />
      </div>
    </div>
  )
}
