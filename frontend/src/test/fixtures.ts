// Response *shapes* for UI tests. The backend tests validate the real compiler
// output; these tests only check that the UI renders what the API returns.
import type { FullAnalysis, PhaseResponse, ToolchainInfo } from '../types/api'

const base = (phase: string, status: PhaseResponse['status'] = 'success', message = `${phase} ok`): PhaseResponse => ({
  phase, status, message, commands: [{ command: ['clang', '-S'], exit_code: 0, duration_ms: 12 }], compiler_stderr: '', warnings: [],
})

export const toolchain = (over: Partial<ToolchainInfo> = {}): ToolchainInfo => ({
  clang: { name: 'clang', available: true, path: '/x/clang', version: 'clang version 23.1.3', error: null },
  opt: { name: 'opt', available: true, path: '/x/opt', version: 'LLVM version 23.1.3', error: null },
  nvcc: { name: 'nvcc', available: false, path: null, version: null, error: 'nvcc was not found' },
  host_triple: 'x86_64-pc-windows-msvc', host_arch: 'x86_64', nvptx_backend: true, system_headers: true,
  system_headers_error: null, ptx_method: 'clang-nvptx',
  capabilities: { tokens: true, ast: true, diagnostics: true, ir: true, optimization: true, assembly: true, ptx: true, individual_passes: true, pass_timeline: true },
  notes: [], allowed_passes: { mem2reg: 'Promote allocas', instcombine: 'Combine instructions' },
  allowed_gpu_archs: ['sm_75', 'sm_80'],
  ...over,
})

export const fullAnalysis = (): FullAnalysis => ({
  tokens: { ...base('tokens'), tokens: [
    { kind: 'int', text: 'int', line: 1, column: 1, flags: ['StartOfLine'], from_macro: false },
    { kind: 'identifier', text: 'main', line: 1, column: 5, flags: [], from_macro: false },
  ], token_count: 2, kind_counts: { int: 1, identifier: 1 }, header_tokens_excluded: 0 },
  ast: { ...base('ast'), nodes: [{ id: '1', kind: 'FunctionDecl', name: 'main', type: 'int (void)', detail: null, line: 1, column: 5, end_line: 3, implicit: false,
    children: [{ id: '2', kind: 'ReturnStmt', name: null, type: null, detail: null, line: 2, column: 5, end_line: 2, implicit: false, children: [] }] }],
    node_count: 2, kind_counts: { FunctionDecl: 1, ReturnStmt: 1 }, raw_text: 'FunctionDecl main', header_decls_excluded: 0 },
  diagnostics: { ...base('diagnostics', 'success', 'Parsing and semantic analysis succeeded.'), diagnostics: [], error_count: 0, warning_count: 0, semantic_ok: true },
  ir: { ...base('ir'), ir: 'define i32 @main() {\n  %1 = alloca i32\n  ret i32 30\n}', opt_level: 'O0', target_triple: 'x86_64-pc-windows-msvc',
    instruction_count: 2, opcode_counts: { alloca: 1, ret: 1 }, functions: [{ name: 'main', instruction_count: 2, block_count: 1, is_declaration: false }],
    explanations: [{ opcode: 'alloca', count: 1, explanation: 'Reserves stack space.' }] },
  optimization: { ...base('optimization', 'success', 'Compared -O0 and -O2'), mode: 'levels', baseline_label: '-O0', optimized_label: '-O2',
    baseline_ir: 'define i32 @main() {\n  %1 = alloca i32\n  ret i32 30\n}', optimized_ir: 'define i32 @main() {\n  ret i32 30\n}',
    baseline_count: 2, optimized_count: 1, opcode_delta: { alloca: [1, 0], ret: [1, 1] },
    function_diffs: [{ name: 'main', status: 'changed', baseline_count: 2, optimized_count: 1,
      lines: [{ op: 'removed', text: '  %1 = alloca i32' }, { op: 'equal', text: '  ret i32 30' }] }],
    observations: ['In `main`: all 1 `alloca` stack slots were eliminated.'],
    pass_timeline: [{ pass_name: 'SROAPass', scope: 'main' }], pass_timeline_note: 'Reported by LLVM itself.' },
  assembly: { ...base('assembly'), asm: 'main:\n\tmov eax, 30\n\tret', filtered_asm: 'main:\n    mov eax, 30\n    ret', target_triple: 'x86_64-pc-windows-msvc',
    arch: 'x86_64', opt_level: 'O0', instruction_count: 2, mnemonic_counts: { mov: 1, ret: 1 }, counting_method: 'Lines that are instructions.',
    source_map: [{ asm_line: 2, source_line: 2 }], comparison: [{ opt_level: 'O0', instruction_count: 2, mnemonic_counts: { mov: 1, ret: 1 } }], explanations: [] },
  ptx: { ...base('ptx', 'unsupported', 'PTX is generated from CUDA source. Select the CUDA language (e.g. the CUDA sample).'), commands: [],
    ptx: '', method: 'clang-nvptx', gpu_arch: 'sm_75', ptx_version: null, target: null, functions: [], register_decls: [], summary: null, comparison: null, explanations: [] },
  metrics: { ...base('metrics'), metrics: [
    { key: 'tokens', label: 'Tokens', value: 2, unit: '', definition: 'Tokens from the main file.', limitation: '' },
    { key: 'ptx_instructions', label: 'PTX instructions', value: null, unit: '', definition: 'PTX statements.', limitation: '' },
  ] },
})
