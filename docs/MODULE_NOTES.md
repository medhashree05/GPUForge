# GPUForge module notes

One note per major module, in the same format: **what** it does, **why** it exists, **input →
output**, the **compiler tool** it uses, **mine vs. Clang/LLVM**, **a failure case** and how it is
handled, and **one design trade-off**. Paths are relative to the repository root.

---

## Backend: infrastructure

### `backend/app/utils/subprocess_runner.py`: `run_tool`
- **What:** the only place that starts external processes.
- **Why:** puts every safety rule for running a compiler in one function: argument lists, no
  shell, timeout, output cap.
- **Input → output:** `list[str]` command, cwd, optional timeout and output limit → `ProcessResult`
  (exit code, stdout, stderr, duration, truncated flag).
- **Tool:** any (clang, opt, nvcc).
- **Mine / theirs:** entirely mine; uses Python's `subprocess.run`.
- **Failure case:** the compiler hangs → `subprocess.TimeoutExpired` → `CompilerTimeoutError` →
  HTTP 504 with "'clang' did not finish within 20 s". Missing executable → HTTP 502.
- **Trade-off:** output is buffered in memory (simple, and lets us measure duration) rather than
  streamed. Capping output bounds the memory cost; the AST phase raises its own cap to 128 MB
  because `<cstdio>` alone produces about 13 MB of JSON.

### `backend/app/utils/source_validation.py`
- **What:** rejects empty or oversized source and file-reading preprocessor tricks.
- **Why:** Clang echoes file contents in diagnostics. `#include "C:/secret"` would turn the tool
  into a file reader.
- **Input → output:** source string → nothing, or raises `SourceValidationError` (HTTP 422).
- **Tool:** none; it runs before any compiler.
- **Mine / theirs:** mine.
- **Failure case:** `#incl\` + newline + `ude "x"` (a line splice hides the directive) is caught
  because validation runs on the text after splices are removed, as the preprocessor sees it.
- **Trade-off:** textual checks instead of a sandbox. Simple and fast, but best-effort.
  Documented as such in the README security section.

### `backend/app/core/toolchain_detection.py`
- **What:** finds clang, opt and nvcc and **executes** them to prove they work; reads the host
  triple, the NVPTX target, available `opt` passes, and whether `<stdio.h>` resolves.
- **Why:** the prompt's rule was "don't assume tools exist". The UI greys out features based on
  this.
- **Input → output:** settings and environment → cached `Toolchain` dataclass.
- **Tool:** `clang --version`, `-print-target-triple`, `-print-targets`, `opt --print-passes`.
- **Mine / theirs:** discovery logic is mine; the facts come from the tools.
- **Failure case:** `nvcc` missing → `ptx_method = "clang-nvptx"` if Clang has NVPTX, otherwise
  `None`, and the PTX phase returns `unsupported` with an explanation.
- **Trade-off:** results are cached for speed. A tool installed while the server runs needs
  "Re-detect" (`POST /api/toolchain/refresh`).

### `backend/app/services/compiler_service.py`
- **What:** turns a validated request into a temp dir with `input.c`/`.cpp`/`.cu` and fixed Clang
  argument lists per language.
- **Why:** one shared definition of "how we invoke Clang" (diagnostic format flags, CUDA
  device-only flags), so every phase behaves consistently.
- **Input → output:** `SourceRequest` + temp dir → `CompileContext`; `run_clang(ctx, args)`.
- **Tool:** clang, opt.
- **Mine / theirs:** mine.
- **Failure case:** without the CUDA SDK, `__global__` would be unknown; we pass `-nocudainc` plus
  `-D__global__=__attribute__((global))` and include Clang's own `__clang_cuda_builtin_vars.h`.
- **Trade-off:** running Clang with cwd = temp dir and a relative filename keeps paths out of the
  output for free, at the cost of always writing a file instead of piping stdin.

---

## Backend: compiler phases

### Lexical: `services/token_service.py` + `parsers/clang_tokens.py`
- **What:** shows the tokens Clang's preprocessor and lexer produce.
- **Why:** first phase of compilation. Also shows that valid tokens ≠ a valid program.
- **Input → output:** stderr of `clang -fsyntax-only -Xclang -dump-tokens` → list of
  `{kind, text, line, column, flags, from_macro}`.
- **Tool:** Clang's lexer and preprocessor.
- **Mine / theirs:** the regex parser, header filtering and macro detection are mine; the tokens
  are Clang's.
- **Failure case:** lines the parser doesn't recognise are counted and reported as a warning
  instead of silently dropped. Diagnostics interleaved on stderr are skipped deliberately.
- **Trade-off:** `-dump-tokens` (preprocessed) instead of `-dump-raw-tokens`. You see macro
  expansions and real token kinds, but comments are absent and `#include`d headers must be
  filtered out.

### Syntax: `services/ast_service.py` + `parsers/clang_ast.py`
- **What:** builds a compact tree of Clang's AST for declarations in the user's file, plus a
  filtered raw text dump.
- **Why:** to show the program's structure as the compiler sees it, including implicit nodes such
  as `ImplicitCastExpr`.
- **Input → output:** `-ast-dump=json` → nested `{kind, name, type, detail, line, children}`.
- **Tool:** Clang's parser and Sema.
- **Mine / theirs:** the tree walker and filter are mine.
- **Failure case (real bug):** Clang's JSON omits `file` and `line` when they equal the
  *previously printed* location. A naive filter mis-classified nodes. Fix: walk all locations in
  dump order and carry the last file forward (`_LocTracker`), mirroring the dumper.
- **Trade-off:** we dump the whole translation unit and filter in Python. That's simple and
  correct but slow for heavy headers; capped at 6000 nodes for the UI.

### Semantic: `services/diagnostics_service.py` + `parsers/clang_diagnostics.py`
- **What:** Clang's errors and warnings with line, column, category, `-W` flag and source snippet.
- **Why:** distinguishes parse errors from semantic errors **using Clang's own categories**
  (`-fdiagnostics-show-category=name`) instead of guessing.
- **Input → output:** stderr of `clang -fsyntax-only -Wall -Wextra` → list of diagnostics,
  counts, `semantic_ok`.
- **Mine / theirs:** the parser is mine; the analysis is entirely Clang's Sema.
- **Failure case:** non-zero exit but no parsable error lines → warning "see raw compiler output",
  and the raw stderr is shown.
- **Trade-off:** parsing text rather than `-fdiagnostics-format=sarif`. The text format is stable
  and simple; SARIF is richer but marked experimental in Clang.

### LLVM IR: `services/ir_service.py` + `parsers/llvm_ir.py`
- **What:** generates `.ll` at the chosen level and counts instructions per function and opcode.
- **Input → output:** `clang -S -emit-llvm -O<n>` → IR text, opcode counts, function table,
  explanations (only for opcodes that occur).
- **Mine / theirs:** the lightweight parser (functions → blocks → instructions) is mine; the IR is
  Clang's.
- **Failure case:** malformed IR makes the parser produce zero instructions rather than crash
  (unit-tested).
- **Trade-off:** a line-based parser instead of linking LLVM's C++ API. No native dependency and
  easy to explain, but it understands less (e.g. no use-def chains).

### Optimization: `services/optimization_service.py` + `parsers/ir_diff.py`
- **What:** compares real IR at two levels (or before/after chosen passes), diffs each function,
  derives observations, and shows which passes LLVM reports as having changed the IR.
- **Why:** the core "what did the optimizer do?" feature.
- **Input → output:** two IR modules → function diffs, opcode deltas, observations, pass timeline.
- **Tool:** `clang -O0/-O2`; `clang -O2 -Xclang -disable-llvm-passes` + `opt -passes=default<O2>
  -print-changed=quiet`; `opt -passes=<list>`.
- **Mine / theirs:** the differ, normalizer, observation rules and replay check are mine; the
  transformations and the pass names are LLVM's.
- **Failure case (real bug):** the first replay used `-O0` IR, but Clang marks `-O0` functions
  `optnone noinline`, so `opt` never inlined and the timeline was wrong. Fix: use
  `-O2 -Xclang -disable-llvm-passes`, the exact IR the `-O2` pipeline starts from. The replay is
  compared with Clang's real output on every request.
- **Trade-off:** observations are rule-based and conservative ("consistent with mem2reg/SROA").
  This avoids over-claiming, but some real effects are described only as count changes.

### Assembly: `services/assembly_service.py` + `parsers/assembly.py`
- **What:** host assembly at the chosen level, a filtered view, instruction counts, a `-O0` vs.
  `-O2` table and source mapping.
- **Input → output:** `clang -S -O<n> -gline-tables-only -ffile-compilation-dir=. [-masm=intel]`
  → filtered asm, mnemonic counts, `[{asm_line, source_line}]`.
- **Mine / theirs:** filtering, counting and mapping are mine; codegen is LLVM's back end.
- **Failure case (real bug):** the filter tested "starts with `.` → directive" before "ends with
  `:` → label", so jump targets like `.LBB0_1:` disappeared. A unit test caught it and the checks
  were reordered.
- **Trade-off:** mapping uses debug line tables (`.loc` on ELF/Mach-O, `.cv_loc` on Windows), so it
  is real compiler data. With optimization one instruction can only map to one line.

### PTX: `services/ptx_service.py` + `parsers/ptx.py`
- **What:** generates PTX (nvcc if installed, else Clang NVPTX), lists kernels, parameters and
  registers, and classifies instructions and memory state spaces.
- **Input → output:** `.cu` source → PTX text + summary (+ optional second level for comparison).
- **Tool:** `nvcc -ptx -arch=sm_XX` or `clang -x cuda --cuda-device-only --cuda-gpu-arch=sm_XX -S`.
- **Mine / theirs:** the PTX parser and classifier are mine; PTX is the compiler's.
- **Failure case:** no PTX toolchain → `unsupported` with an explanation, and **never** placeholder
  PTX (tested).
- **Trade-off:** static classification by opcode prefix (`ld.global`, `bar.sync`). Easy to verify,
  but says nothing about runtime cost; the UI shows that warning with every PTX result.

### Orchestration: `services/analysis_service.py`
- **What:** runs every phase for one request and builds the metrics report.
- **Failure case:** if diagnostics fail, codegen phases become `skipped`. If a tool is missing,
  that phase becomes `unsupported` while the others still run.
- **Trade-off:** one big `/analyze/full` request (simple UI, consistent snapshot) instead of lazy
  per-tab requests (faster first paint). Per-phase endpoints exist for API users.

---

## Frontend

### `frontend/src/App.tsx`
- **What:** layout and state (source, settings, result, selected phase, history, focus line).
- **Why:** keeping state at the top preserves source and settings while navigating phases.
- **Trade-off:** plain React state instead of a state library; the app has one screen.

### `features/editor/SourceEditor.tsx`
- Monaco editor plus sample, language, opt level, CPU/PTX and `sm_XX` selectors. PTX is disabled
  when no PTX toolchain is detected. Highlights the "focus line" set by other views.

### `features/pipeline/CompilationPipeline.tsx` + `PhaseNavigation.tsx`
- A React Flow diagram and a tab strip showing each phase's status (completed, failed,
  unsupported, skipped, not run). Animated edges mark successful phases.
- **Trade-off:** React Flow is heavier than a CSS list, but it makes the "pipeline" idea visual.

### `components/CodeView.tsx`
- Read-only Monaco with line numbers, search-highlighting, copy and line-click callbacks. Reused
  for IR, assembly, PTX and the raw AST.
- **Failure case (real bug):** a highlight requested before Monaco finished mounting was lost.
  Fix: keep the editor instance in React state so the effect re-runs after mount.

### `features/optimization/OptimizationComparison.tsx` + `diffRows.ts`
- Mode switch (levels or passes), summary cards, observations, pass timeline, side-by-side diff
  (`toSideBySide` pairs removed and added runs), opcode table and a Monaco DiffEditor for raw
  output.

### `features/assembly/AssemblyViewer.tsx`
- Two-way mapping: click an instruction to highlight its source line; select a source line
  elsewhere to highlight its instructions.

### `features/ptx/PTXViewer.tsx`
- Kernel and parameter cards, register declarations, class and state-space table, comparison
  with another level, and an explicit "unsupported" view that shows which tools were checked.

### `services/api.ts`
- A typed fetch client. It turns backend error JSON and network failures into `ApiError` with a
  readable message, which the UI shows in `ErrorState`.
