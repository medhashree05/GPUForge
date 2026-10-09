import { describe, expect, it } from 'vitest'
import { toSideBySide } from './diffRows'

describe('toSideBySide', () => {
  it('pairs removed runs with following added runs', () => {
    const rows = toSideBySide([
      { op: 'equal', text: 'entry:' },
      { op: 'removed', text: 'a' },
      { op: 'removed', text: 'b' },
      { op: 'added', text: 'c' },
      { op: 'equal', text: 'ret' },
      { op: 'added', text: 'd' },
    ])
    expect(rows).toEqual([
      { left: 'entry:', right: 'entry:', kind: 'equal' },
      { left: 'a', right: 'c', kind: 'changed' },
      { left: 'b', right: null, kind: 'removed' },
      { left: 'ret', right: 'ret', kind: 'equal' },
      { left: null, right: 'd', kind: 'added' },
    ])
  })
})
