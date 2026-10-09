// Bundle Monaco locally (no CDN) and register simple syntax highlighters for
// LLVM IR, target assembly and PTX. These are display-only tokenizers.
// edcore.main = editor + core features (find, diff…) without the ~80 bundled
// languages; we only add C/C++ plus our own tokenizers below.
import * as monaco from 'monaco-editor/esm/vs/editor/edcore.main'
import 'monaco-editor/esm/vs/basic-languages/cpp/cpp.contribution'
import { loader } from '@monaco-editor/react'
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

self.MonacoEnvironment = { getWorker: () => new EditorWorker() }
loader.config({ monaco })

monaco.languages.register({ id: 'llvm-ir' })
monaco.languages.setMonarchTokensProvider('llvm-ir', {
  tokenizer: {
    root: [
      [/;.*$/, 'comment'],
      [/"[^"]*"/, 'string'],
      [/^\s*(define|declare)\b/, 'keyword'],
      [/^[\w.$-]+:/, 'type.identifier'],
      [/\b(alloca|load|store|add|sub|mul|sdiv|udiv|srem|urem|shl|lshr|ashr|and|or|xor|icmp|fcmp|br|switch|call|invoke|ret|phi|select|getelementptr|sext|zext|trunc|bitcast|fadd|fsub|fmul|fdiv|fneg|sitofp|fptosi|unreachable|tail|freeze)\b/, 'keyword'],
      [/\b(i\d+|ptr|void|float|double|half|label|x86_fp80)\b/, 'type'],
      [/@[\w.$"-]+/, 'variable.predefined'],
      [/%[\w.$"-]+/, 'variable'],
      [/![\w.]+/, 'annotation'],
      [/#\d+/, 'annotation'],
      [/-?\d+(\.\d+)?/, 'number'],
    ],
  },
})

monaco.languages.register({ id: 'target-asm' })
monaco.languages.setMonarchTokensProvider('target-asm', {
  tokenizer: {
    root: [
      [/(#|\/\/).*$/, 'comment'],
      [/^\s*\.[\w.]+/, 'annotation'],
      [/^[\w.$@?]+:/, 'type.identifier'],
      [/^\s+[a-z][\w.]*/, 'keyword'],
      [/\b(r[a-z0-9]+|e[a-z]{2}|[re]?[sb]p|x\d+|w\d+|xmm\d+|ymm\d+)\b/, 'variable'],
      [/\b(dword|qword|word|byte)\s+ptr\b/, 'type'],
      [/[#$]?-?(0x[0-9a-f]+|\d+)\b/, 'number'],
      [/"[^"]*"/, 'string'],
    ],
  },
})

monaco.languages.register({ id: 'ptx' })
monaco.languages.setMonarchTokensProvider('ptx', {
  tokenizer: {
    root: [
      [/\/\/.*$/, 'comment'],
      [/\.(visible|entry|func|param|reg|shared|global|local|const|version|target|address_size|align|ptr)\b/, 'annotation'],
      [/\$[\w]+:?/, 'type.identifier'],
      [/@!?%p\d+/, 'keyword.control'],
      [/^\s+[a-z][\w.]*/, 'keyword'],
      [/%[\w.]+/, 'variable'],
      [/-?(0[fFdDxX][0-9a-fA-F]+|\d+)/, 'number'],
    ],
  },
})

export { monaco }
