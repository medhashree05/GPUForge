import type { DiffLine } from '../../types/api'

export interface DiffRow {
  left: string | null
  right: string | null
  kind: 'equal' | 'changed' | 'removed' | 'added'
}

/** Turn the backend's unified diff (equal/removed/added) into side-by-side rows,
 *  pairing each run of removed lines with the run of added lines that follows. */
export function toSideBySide(lines: DiffLine[]): DiffRow[] {
  const rows: DiffRow[] = []
  let i = 0
  while (i < lines.length) {
    if (lines[i].op === 'equal') {
      rows.push({ left: lines[i].text, right: lines[i].text, kind: 'equal' })
      i++
      continue
    }
    const removed: string[] = []
    const added: string[] = []
    while (i < lines.length && lines[i].op === 'removed') removed.push(lines[i++].text)
    while (i < lines.length && lines[i].op === 'added') added.push(lines[i++].text)
    for (let k = 0; k < Math.max(removed.length, added.length); k++) {
      const l = removed[k] ?? null
      const r = added[k] ?? null
      rows.push({ left: l, right: r, kind: l !== null && r !== null ? 'changed' : l !== null ? 'removed' : 'added' })
    }
  }
  return rows
}
