import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { createElement } from 'react'

// Vitest runs without globals, so Testing Library's auto-cleanup must be registered.
afterEach(() => cleanup())

// Monaco cannot run in jsdom: replace editors with plain elements.
vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange, options }: { value: string; onChange?: (v: string) => void; options?: { readOnly?: boolean } }) =>
    createElement('textarea', {
      'data-testid': options?.readOnly ? 'code-view' : 'source-editor',
      value,
      readOnly: options?.readOnly,
      onChange: (e: { target: { value: string } }) => onChange?.(e.target.value),
    }),
  DiffEditor: ({ original, modified }: { original: string; modified: string }) =>
    createElement('div', { 'data-testid': 'diff-editor' }, `${original}\n---\n${modified}`),
}))

// React Flow needs real layout; render each node as a clickable button instead.
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ nodes, onNodeClick }: { nodes: { id: string; data: { label: string; status: string } }[]; onNodeClick: (e: unknown, n: unknown) => void }) =>
    createElement('div', { 'data-testid': 'pipeline' },
      nodes.map((n) => createElement('button', {
        key: n.id, 'data-status': n.data.status, onClick: () => onNodeClick({}, n),
      }, `node:${n.data.label}`))),
  Background: () => null,
  Handle: () => null,
  Position: { Top: 'top', Bottom: 'bottom' },
}))
