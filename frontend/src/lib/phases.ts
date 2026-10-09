import type { FullAnalysis, PhaseStatus } from '../types/api'

export type PhaseId =
  | 'source' | 'tokens' | 'ast' | 'diagnostics' | 'ir' | 'optimization' | 'assembly' | 'ptx' | 'metrics'

export interface PhaseInfo {
  id: PhaseId
  label: string
  short: string
  explanation: string
}

// Educational view of the workflow. Clang does not literally run these as
// separate isolated programs; GPUForge invokes it once per view.
export const PHASES: PhaseInfo[] = [
  {
    id: 'source', label: 'Source Code', short: 'Source',
    explanation: 'The program text you wrote. Nothing has been analyzed yet.',
  },
  {
    id: 'tokens', label: 'Lexical Analysis', short: 'Tokens',
    explanation:
      'The lexer (and preprocessor) turns characters into tokens: keywords, identifiers, literals, ' +
      'punctuation. Tokenizing successfully does NOT mean the program is valid. `return x + ;` ' +
      'tokenizes fine but fails to parse.',
  },
  {
    id: 'ast', label: 'Syntax / AST', short: 'AST',
    explanation:
      "The parser checks the grammar and builds Clang's Abstract Syntax Tree. Unlike a concrete parse " +
      'tree, the AST omits pure syntax (parentheses, semicolons) and records meaning-bearing structure ' +
      '(declarations, expressions, statements), including nodes Clang inserts, such as implicit casts.',
  },
  {
    id: 'diagnostics', label: 'Semantic Diagnostics', short: 'Diagnostics',
    explanation:
      'Semantic analysis (Clang Sema, which runs while parsing) checks types, declarations and calls. ' +
      "Errors and warnings below are Clang's own messages and categories from `clang -fsyntax-only`.",
  },
  {
    id: 'ir', label: 'LLVM IR', short: 'IR',
    explanation:
      "LLVM IR is the compiler's target-independent intermediate representation, in SSA form. It is " +
      'not machine code: a back end still has to translate it for a specific CPU or GPU.',
  },
  {
    id: 'optimization', label: 'Optimization', short: 'Optimize',
    explanation:
      "LLVM's optimizer transforms IR into equivalent, usually faster IR. The comparison shows only " +
      'what actually changed between two real compiler outputs.',
  },
  {
    id: 'assembly', label: 'CPU Assembly', short: 'Assembly',
    explanation:
      'The back end lowers IR to assembly for one specific architecture (detected from your Clang). ' +
      'Assembly is architecture-specific: x86-64 and AArch64 output look completely different.',
  },
  {
    id: 'ptx', label: 'NVIDIA PTX', short: 'PTX',
    explanation:
      "PTX is NVIDIA's virtual GPU instruction set. The driver/ptxas later compiles it to the GPU's " +
      'real machine code (SASS). Generating PTX does not require a GPU.',
  },
  {
    id: 'metrics', label: 'Analysis Report', short: 'Report',
    explanation: 'Counts and comparisons derived from this run. Every metric states its definition and limits.',
  },
]

export function phaseStatus(id: PhaseId, result: FullAnalysis | null): PhaseStatus | 'idle' {
  if (id === 'source') return result ? 'success' : 'idle'
  if (!result) return 'idle'
  return result[id].status
}

export const STATUS_STYLE: Record<PhaseStatus | 'idle', { dot: string; text: string; label: string }> = {
  success: { dot: 'bg-emerald-400', text: 'text-emerald-300', label: 'Completed' },
  failed: { dot: 'bg-red-400', text: 'text-red-300', label: 'Failed' },
  unsupported: { dot: 'bg-slate-500', text: 'text-slate-400', label: 'Unsupported' },
  skipped: { dot: 'bg-amber-400', text: 'text-amber-300', label: 'Skipped' },
  idle: { dot: 'bg-slate-700', text: 'text-slate-500', label: 'Not run' },
}
