// TypeScript mirrors of backend/app/models/responses.py.

export type Language = 'c' | 'cpp' | 'cuda'
export type OptLevel = 'O0' | 'O1' | 'O2' | 'O3' | 'Os' | 'Oz'
export type Target = 'cpu' | 'ptx'
export type PhaseStatus = 'success' | 'failed' | 'unsupported' | 'skipped'

export interface SourceRequest {
  source: string
  language: Language
  opt_level: OptLevel
  target: Target
  gpu_arch: string
}

export interface OptimizationRequest extends SourceRequest {
  baseline_level: OptLevel
  optimized_level: OptLevel
  passes: string[]
}

export interface CommandInfo {
  command: string[]
  exit_code: number
  duration_ms: number
}

export interface PhaseResponse {
  phase: string
  status: PhaseStatus
  message: string
  commands: CommandInfo[]
  compiler_stderr: string
  warnings: string[]
}

export interface ToolStatus {
  name: string
  available: boolean
  path: string | null
  version: string | null
  error: string | null
}

export interface ToolchainInfo {
  clang: ToolStatus
  opt: ToolStatus
  nvcc: ToolStatus
  host_triple: string | null
  host_arch: string | null
  nvptx_backend: boolean
  system_headers: boolean
  system_headers_error: string | null
  ptx_method: 'nvcc' | 'clang-nvptx' | null
  capabilities: Record<string, boolean>
  notes: string[]
  allowed_passes: Record<string, string>
  allowed_gpu_archs: string[]
}

export interface Token {
  kind: string
  text: string
  line: number | null
  column: number | null
  flags: string[]
  from_macro: boolean
}

export interface TokensResponse extends PhaseResponse {
  tokens: Token[]
  token_count: number
  kind_counts: Record<string, number>
  header_tokens_excluded: number
}

export interface ASTNode {
  id: string
  kind: string
  name: string | null
  type: string | null
  detail: string | null
  line: number | null
  column: number | null
  end_line: number | null
  implicit: boolean
  children: ASTNode[]
}

export interface ASTResponse extends PhaseResponse {
  nodes: ASTNode[]
  node_count: number
  kind_counts: Record<string, number>
  raw_text: string
  header_decls_excluded: number
}

export interface Diagnostic {
  severity: 'error' | 'warning' | 'note' | 'remark' | 'fatal error'
  message: string
  line: number | null
  column: number | null
  category: string | null
  flag: string | null
  in_main_file: boolean
  snippet: string | null
}

export interface DiagnosticsResponse extends PhaseResponse {
  diagnostics: Diagnostic[]
  error_count: number
  warning_count: number
  semantic_ok: boolean
}

export interface InstructionExplanation {
  opcode: string
  count: number
  explanation: string
}

export interface IRFunction {
  name: string
  instruction_count: number
  block_count: number
  is_declaration: boolean
}

export interface IRResponse extends PhaseResponse {
  ir: string
  opt_level: string
  target_triple: string | null
  instruction_count: number
  opcode_counts: Record<string, number>
  functions: IRFunction[]
  explanations: InstructionExplanation[]
}

export interface DiffLine {
  op: 'equal' | 'added' | 'removed'
  text: string
}

export interface FunctionDiff {
  name: string
  status: 'changed' | 'unchanged' | 'removed' | 'added'
  baseline_count: number
  optimized_count: number
  lines: DiffLine[]
}

export interface PassChange {
  pass_name: string
  scope: string
}

export interface OptimizationResponse extends PhaseResponse {
  mode: 'levels' | 'passes'
  baseline_label: string
  optimized_label: string
  baseline_ir: string
  optimized_ir: string
  baseline_count: number
  optimized_count: number
  opcode_delta: Record<string, [number, number]>
  function_diffs: FunctionDiff[]
  observations: string[]
  pass_timeline: PassChange[]
  pass_timeline_note: string
}

export interface SourceMapEntry {
  asm_line: number
  source_line: number
}

export interface AsmVariant {
  opt_level: string
  instruction_count: number
  mnemonic_counts: Record<string, number>
}

export interface AssemblyResponse extends PhaseResponse {
  asm: string
  filtered_asm: string
  target_triple: string | null
  arch: string | null
  opt_level: string
  instruction_count: number
  mnemonic_counts: Record<string, number>
  counting_method: string
  source_map: SourceMapEntry[]
  comparison: AsmVariant[]
  explanations: InstructionExplanation[]
}

export interface PTXFunction {
  name: string
  is_kernel: boolean
  instruction_count: number
  params: string[]
}

export interface PTXSummary {
  opt_level: string
  instruction_count: number
  class_counts: Record<string, number>
  opcode_counts: Record<string, number>
  memory_ops: Record<string, number>
  branch_count: number
}

export interface PTXResponse extends PhaseResponse {
  ptx: string
  method: string | null
  gpu_arch: string
  ptx_version: string | null
  target: string | null
  functions: PTXFunction[]
  register_decls: string[]
  summary: PTXSummary | null
  comparison: PTXSummary | null
  explanations: InstructionExplanation[]
}

export interface Metric {
  key: string
  label: string
  value: number | string | null
  unit: string
  definition: string
  limitation: string
}

export interface MetricsResponse extends PhaseResponse {
  metrics: Metric[]
}

export interface FullAnalysis {
  tokens: TokensResponse
  ast: ASTResponse
  diagnostics: DiagnosticsResponse
  ir: IRResponse
  optimization: OptimizationResponse
  assembly: AssemblyResponse
  ptx: PTXResponse
  metrics: MetricsResponse
}

export interface Sample {
  id: string
  title: string
  language: Language
  description: string
  source: string
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: { field: string; message: string }[] }
}
