# GPUForge — Compiler Pipeline Visualization and Optimization Analyzer

GPUForge is a local web application that takes C, C++ or CUDA source code and shows what a real
compiler does with it, phase by phase: tokens, AST, semantic diagnostics, LLVM IR, optimization
changes, CPU assembly and NVIDIA PTX.

**GPUForge is not a compiler.** It runs **Clang and LLVM**, collects their real outputs, and
implements the analysis, comparison, reporting and visualization layers itself. Every output shown
in the UI was produced by a compiler during that request. Nothing is hard-coded or simulated.

```
 Source ─► Lexical ─► Syntax/AST ─► Semantic ─► LLVM IR ─► Optimization ─► Target code ─► Report
 (editor)  (tokens)   (Clang AST)   (Clang      (clang     (-O0 vs -O2,    (x86-64 asm,
                                     Sema)       -emit-llvm) opt passes)     NVIDIA PTX)
```

---

## Contents
1. [Features and status checklist](#1-features-and-status-checklist)
2. [What GPUForge implements itself vs. what Clang/LLVM provides](#2-what-gpuforge-implements-itself-vs-what-clangllvm-provides)
3. [Architecture](#3-architecture)
4. [Setup (Windows and Linux)](#4-setup)
5. [Running](#5-running)
6. [How source code flows through each phase](#6-how-source-code-flows-through-each-phase)
7. [API reference](#7-api-reference)
8. [Testing](#8-testing)
9. [Security model](#9-security-model)
10. [CPU-only vs. CUDA: what works where](#10-cpu-only-vs-cuda-what-works-where)
11. [Known limitations](#11-known-limitations)
12. [Troubleshooting](#12-troubleshooting)

Further documents: [`docs/MODULE_NOTES.md`](docs/MODULE_NOTES.md) (developer notes for every module) ·
[`docs/INTERVIEW_GUIDE.md`](docs/INTERVIEW_GUIDE.md).

---

## 1. Features and status checklist

Verified on the development machine: Windows 11, Clang/LLVM 23.1.3 (`x86_64-pc-windows-msvc`),
MSVC Build Tools 14.51, no CUDA Toolkit.

| Feature | Implemented | Automated tests | Verified end-to-end in a browser |
|---|---|---|---|
| Source editor (Monaco), 9 samples, C/C++/CUDA, opt level, CPU/PTX target | ✅ | ✅ frontend | ✅ |
| Lexical analysis: Clang token dump, kind filter, search, line:col, macro flag | ✅ | ✅ parser + integration | ✅ |
| AST: expandable tree, node-type search, raw `-ast-dump` view, header filtering | ✅ | ✅ | ✅ |
| Diagnostics: Clang errors/warnings, Clang's own category, `-W` flag, snippet | ✅ | ✅ (5 error kinds) | ✅ |
| LLVM IR: highlighted viewer, search, copy, opcode counts, explanations | ✅ | ✅ | ✅ |
| Optimization: level comparison, instruction diff, observations, opcode deltas | ✅ | ✅ | ✅ |
| Optimization: LLVM-reported pass timeline (`opt -print-changed`), checked against Clang's output | ✅ | ✅ | ✅ |
| Optimization: run individual passes (`opt -passes=…`, allow-listed) | ✅ | ✅ | ✅ |
| CPU assembly: host-target detection, filtered/raw, counts, -O0/-O2 table, source mapping | ✅ | ✅ | ✅ |
| PTX via Clang NVPTX backend (no CUDA Toolkit needed) | ✅ | ✅ | ✅ |
| PTX via `nvcc` | ✅ code path | ⚠️ mocked only | ❌ not testable here (no CUDA Toolkit) |
| PTX analysis: kernels, params, registers, instruction classes, state spaces, level comparison | ✅ | ✅ | ✅ |
| Metrics report with definitions, limitations, "Unavailable" | ✅ | ✅ | ✅ |
| Interactive pipeline diagram (React Flow), phase status, unsupported vs. failed vs. skipped | ✅ | ✅ | ✅ |
| Session history, toolchain settings panel | ✅ | ✅ (partially) | ✅ |
| Kernel *execution* / GPU benchmarking | ❌ out of scope by design | — | — |

## 2. What GPUForge implements itself vs. what Clang/LLVM provides

| Clang / LLVM provide (unchanged, invoked as subprocesses) | GPUForge implements |
|---|---|
| Preprocessing and tokenization (`-Xclang -dump-tokens`) | Token-dump parser; main-file vs. header filtering; macro detection |
| Parsing and the AST (`-ast-dump=json`, `-ast-dump`) | JSON AST walker with location tracking; compact tree; text-dump filter |
| Semantic analysis and diagnostics (`-fsyntax-only`) | Diagnostic parser (severity, Clang category, `-W` flag, source snippet) |
| LLVM IR generation (`-S -emit-llvm`) | Lightweight LLVM IR parser (functions, blocks, instructions, opcodes) |
| The optimizer (`-O1/-O2/…`, `opt -passes=…`, `-print-changed`) | IR differ (name-normalized), evidence-based observation rules, pass-timeline parser, replay check |
| Code generation for x86-64/AArch64 (`-S`) and NVPTX | Assembly filter and instruction counter, line-table source mapping, PTX parser and classifier |
| — | FastAPI backend, validation and security layer, toolchain detection, React UI |

GPUForge does **not** contain a lexer, parser, type checker, optimizer or code generator of its own.

## 3. Architecture

```
┌──────────────────────── Browser (React + TypeScript + Vite) ────────────────────────┐
│ SourceEditor (Monaco) │ CompilationPipeline (React Flow) │ PhaseNavigation (tabs)  │
│ TokenViewer · ASTViewer · DiagnosticsPanel · IRViewer · OptimizationComparison      │
│ AssemblyViewer · PTXViewer · MetricsPanel · CompilationHistory · SettingsPanel      │
│                services/api.ts  ──  fetch('/api/…')  (Vite dev proxy)               │
└───────────────────────────────────────┬─────────────────────────────────────────────┘
                                        │ JSON over HTTP (Pydantic-validated)
┌───────────────────────────────────────▼─────────── FastAPI backend (Python) ─────────┐
│ api/          health · toolchain · compilation   (routes, request models)             │
│ services/     token · ast · diagnostics · ir · optimization · assembly · ptx · analysis│
│ parsers/      clang_tokens · clang_ast · clang_diagnostics · llvm_ir · ir_diff ·      │
│               assembly · ptx · explanations      (pure text → data, unit-tested)      │
│ core/         config · toolchain_detection · security · errors                        │
│ utils/        subprocess_runner (list args, timeout, output cap) · source_validation  │
└───────────────────────────────────────┬──────────────────────────────────────────────┘
                                        │ subprocess (no shell), per-request temp dir
                         ┌──────────────▼──────────────┐
                         │ clang · opt · (nvcc)        │  real compiler toolchain
                         └─────────────────────────────┘
```

Request lifecycle: validate source → create private temp dir → write `input.c` → run Clang with a
fixed argument list (cwd = temp dir) → parse output → delete temp dir → return JSON.

```
backend/
  app/main.py                FastAPI app, error handlers, body-size limit
  app/api/                   routes.py, health.py, toolchain.py, compilation.py
  app/services/              one module per phase + analysis_service (full run + metrics)
  app/parsers/               pure parsers for each compiler output format
  app/models/                requests.py, responses.py (Pydantic)
  app/core/                  config, toolchain_detection, security, errors
  app/utils/                 subprocess_runner, source_validation
  tests/                     unit, error-path (mocked) and integration tests + real fixtures
frontend/
  src/App.tsx                shell: layout, state, phase routing
  src/features/<phase>/      one folder per phase view
  src/components/            CodeView (read-only Monaco), shared UI
  src/services/api.ts        API client      src/types/api.ts   API types
  src/hooks/useBackend.ts    toolchain + analysis hooks
  src/lib/                   monaco setup (+ LLVM IR/asm/PTX highlighters), phase metadata
samples/                     example programs + samples.json (served by the API, used by tests)
docs/                        MODULE_NOTES.md, INTERVIEW_GUIDE.md
```

## 4. Setup

### Requirements
| Tool | Needed for | Notes |
|---|---|---|
| Python ≥ 3.11 | backend | developed on 3.13 |
| Node.js ≥ 20 | frontend | developed on 22.12 |
| **Clang** | every compiler phase | required |
| LLVM **`opt`** | pass timeline, individual passes | optional; level comparison still works without it |
| Standard headers | programs that `#include` | MSVC Build Tools + Windows SDK (Windows), libc dev headers (Linux) |
| Clang with NVPTX target **or** CUDA Toolkit (`nvcc`) | PTX phase | optional; official LLVM builds include NVPTX |

### Installing the toolchain

**Windows.** The `winget`/`.exe` LLVM installer omits `opt`. Use the official archive instead,
which contains `clang` and `opt`:

1. Download `clang+llvm-<version>-x86_64-pc-windows-msvc.tar.xz` from
   <https://github.com/llvm/llvm-project/releases> and extract it, e.g. to `D:\tools\`.
2. Install **Visual Studio Build Tools** with the "Desktop development with C++" workload
   (provides the C/C++ headers and the Windows SDK that Clang uses).
3. Point GPUForge to it in `backend/.env`:
   `GPUFORGE_LLVM_BIN_DIR=D:\tools\clang+llvm-<version>-x86_64-pc-windows-msvc\bin`

**Linux (Debian/Ubuntu).**
```bash
sudo apt install clang llvm build-essential        # clang, opt, libc headers
# or the newest release: https://apt.llvm.org  (then GPUFORGE_LLVM_BIN_DIR=/usr/lib/llvm-<N>/bin)
```

**Optional CUDA Toolkit.** Install from NVIDIA. GPUForge finds `nvcc` on `PATH`, through
`CUDA_PATH`, or through `GPUFORGE_NVCC_PATH`. A GPU is not needed for PTX generation.

### Install the application
```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux: cp .env.example .env   — then edit paths

# Frontend
cd ../frontend
npm install
```

### Toolchain detection
On first use the backend locates each tool (explicit path → `GPUFORGE_LLVM_BIN_DIR` → `PATH` →
default install directory) and **runs** it (`--version`, `-print-target-triple`, `-print-targets`,
`opt --print-passes`, plus a `#include <stdio.h>` probe). Only tools that actually work are
offered. See `GET /api/toolchain`, or the **Toolchain** button in the UI, which can also re-detect.

## 5. Running

```bash
# terminal 1
cd backend && .venv\Scripts\python -m uvicorn app.main:app --port 8000
# terminal 2
cd frontend && npm run dev
```
Open <http://localhost:5173>. Load a sample, press **Compile & Analyze** (Ctrl+Enter), then explore the
tabs or the pipeline diagram. Interactive API docs are at <http://127.0.0.1:8000/docs>.

## 6. How source code flows through each phase

| Phase | Command GPUForge runs (simplified) | What the UI shows |
|---|---|---|
| Lexical | `clang -fsyntax-only -Xclang -dump-tokens input.c` | Token kind, text, line:col, flags. Tokens come from the preprocessor (macros expanded). Header tokens are excluded and counted. |
| Syntax/AST | `clang -fsyntax-only -Xclang -ast-dump=json` and `-ast-dump` | Tree of declarations from your file; raw text dump. |
| Semantic | `clang -fsyntax-only -Wall -Wextra -fdiagnostics-show-category=name` | Errors and warnings with Clang's category (Parse Issue, Semantic Issue, …). |
| LLVM IR | `clang -S -emit-llvm -O<n>` | The `.ll` file, opcode counts, explanations for opcodes that occur. |
| Optimization | `clang -S -emit-llvm -O0` and `-O2`; `clang -O2 -Xclang -disable-llvm-passes` → `opt -passes=default<O2> -print-changed=quiet` | Side-by-side instruction diff, observations, the passes LLVM reports as having changed the IR. |
| Assembly | `clang -S -O<n> -gline-tables-only -masm=intel` (+ `-O0`/`-O2` for comparison) | Filtered assembly, counts, source ↔ assembly mapping. |
| PTX | `clang -x cuda --cuda-device-only --cuda-gpu-arch=sm_XX -S` or `nvcc -ptx -arch=sm_XX` | PTX, kernels, registers, instruction classes, memory state spaces. |

If semantic analysis fails, the code-generation phases are marked **skipped**, not failed or
fabricated. A phase that the toolchain or language cannot support (e.g. PTX for C source) is marked
**unsupported**.

## 7. API reference

All endpoints are under `/api`. Errors always have the shape
`{"error": {"code": "...", "message": "...", "details"?: [...]}}`. Stack traces are never returned.

| Method & path | Body | Returns |
|---|---|---|
| `GET /health` | – | `{status: "ok"}` |
| `GET /toolchain` | – | tools, versions, host triple, capabilities, allowed passes and GPU archs |
| `POST /toolchain/refresh` | – | re-runs detection |
| `GET /samples` | – | example programs |
| `POST /analyze/tokens` | `SourceRequest` | `TokensResponse` |
| `POST /analyze/ast` | `SourceRequest` | `ASTResponse` |
| `POST /analyze/diagnostics` | `SourceRequest` | `DiagnosticsResponse` |
| `POST /compile/ir` | `SourceRequest` | `IRResponse` |
| `POST /analyze/optimization` | `OptimizationRequest` | `OptimizationResponse` |
| `POST /compile/assembly` | `AssemblyRequest` | `AssemblyResponse` |
| `POST /compile/ptx` | `PTXRequest` | `PTXResponse` |
| `POST /analyze/metrics` | `SourceRequest` | `MetricsResponse` |
| `POST /analyze/full` | `SourceRequest` | all of the above in one response (used by the UI) |

```jsonc
// SourceRequest
{ "source": "int main(void){return 0;}", "language": "c|cpp|cuda",
  "opt_level": "O0|O1|O2|O3|Os|Oz", "target": "cpu|ptx", "gpu_arch": "sm_75" }
// OptimizationRequest = SourceRequest + { "baseline_level": "O0", "optimized_level": "O2", "passes": ["mem2reg"] }
// AssemblyRequest     = SourceRequest + { "intel_syntax": true }
// PTXRequest          = SourceRequest + { "compare_opt_level": "O2" | null }
```

Every phase response includes `status` (`success|failed|unsupported|skipped`), `message`, `warnings`,
`compiler_stderr` and `commands` (the exact argument lists that were run, with exit codes and
durations). HTTP status codes: `422` invalid request or rejected source, `413` body too large,
`503` required tool missing, `504` compiler timeout, `502` tool could not be executed.

## 8. Testing

```bash
cd backend  && .venv\Scripts\python -m pytest -q     # 78 tests
cd frontend && npm test                               # 10 tests
cd frontend && npx tsc -b && npx eslint .             # type-check + lint
```

* **Parser unit tests** (`tests/test_parsers.py`) run against **real compiler output captured from
  Clang** in `tests/fixtures/`. They work without Clang installed. Regenerate the fixtures with
  `python -m tests.fixtures.regenerate`.
* **Error-path tests** (`tests/test_error_paths.py`) mock subprocesses and toolchains: missing
  compiler, timeout, missing executable, malformed output, PTX unavailable, missing `opt`, hidden
  stack traces.
* **Validation tests** cover empty, oversized and malformed payloads, plus include/embed attacks.
* **Integration tests** (`tests/test_integration.py`) run the real Clang. They are skipped
  automatically if Clang is absent, and the PTX test is skipped if no PTX toolchain exists. They
  check properties of the actual output (e.g. `main` folds to `ret i32 55` at `-O2`, `mem2reg`
  removes all `alloca`s, assembly instruction count drops from `-O0` to `-O2`).
* **Frontend tests** (Vitest + Testing Library) cover editing, submission, loading and error
  states, phase switching, output display, optimization comparison and missing-toolchain messages.
  Monaco and React Flow are replaced by simple stand-ins because they cannot run in jsdom.
* The full UI workflow was also verified manually in Microsoft Edge with the real backend.

## 9. Security model

GPUForge runs a native compiler on code typed into a web page, so source is treated as untrusted:

* Executables are fixed paths found at startup. Users choose only from enumerations (language, opt
  level, allow-listed passes, allow-listed GPU archs) and never supply flags.
* `subprocess.run([...], shell=False)` always. Arguments are never concatenated into a shell string.
* Every process has a timeout (default 20 s). Output size is capped.
* Source is limited to 64 KiB and request bodies are limited before parsing.
* Each request runs in its own temporary directory, which is deleted afterwards. Clang runs with
  the temp dir as its working directory and a relative filename, and `-ffile-compilation-dir=.` is
  used, so server paths do not appear in outputs.
* Quoted `#include "…"`, `#embed`, computed (macro) includes, path-traversal header names, quoted
  `__has_include`, trigraphs, and line-splice tricks that hide these are rejected, so compiler
  output cannot be used to read arbitrary files.
* Generated programs are **never executed**. GPUForge only compiles.
* Internal exceptions are logged on the server. Clients receive a generic message.

**Remaining limitations:** this is a best-effort design for a **local, single-user** tool, not a
sandbox. Clang still runs with the user's OS permissions, a crafted input could still make Clang
consume CPU or memory until the timeout, and `<system>` headers remain readable by design. Do not
expose the backend on a network without OS-level isolation (container/VM, resource limits, no
network).

## 10. CPU-only vs. CUDA: what works where

| Capability | Clang only | + `opt` | + Clang NVPTX target | + CUDA Toolkit | + NVIDIA GPU |
|---|---|---|---|---|---|
| Tokens, AST, diagnostics, IR, level comparison, assembly, metrics | ✅ | ✅ | ✅ | ✅ | ✅ |
| Pass timeline, individual passes | – | ✅ | ✅ | ✅ | ✅ |
| PTX from CUDA (minimal built-in subset: `__global__`, `__device__`, `__shared__`, `threadIdx`…, `__syncthreads`) | – | – | ✅ | ✅ | ✅ |
| PTX from CUDA using the full CUDA runtime headers | – | – | – | ✅ | ✅ |
| Running kernels / benchmarking | not provided by GPUForge in any configuration |

## 11. Known limitations

* **Static counts are not performance.** Fewer IR, assembly or PTX instructions do not imply faster
  code. Loops execute their body many times, and inlining or unrolling can grow code while
  speeding it up.
* **Pass attribution** comes only from `opt -print-changed` replaying the optimization pipeline on
  Clang's pre-optimization IR. GPUForge checks that the replay reproduces Clang's real output (same
  instructions and block structure, ignoring value names) and labels the timeline approximate if it
  does not. Observations in the diff never name a pass, only "consistent with …".
* The IR differ matches lines textually after normalizing SSA names. A moved or renumbered
  instruction can appear as removed+added.
* Token dumps are post-preprocessing (`-dump-tokens`): comments are absent and macro expansions
  appear at their use site.
* The AST view lists declarations from your file only. Implicit declarations and those from
  headers are counted but hidden. Very large ASTs are truncated at 6000 nodes.
* Assembly source mapping uses debug line tables. With optimization, one instruction maps to one
  line even when it implements several.
* CUDA without the CUDA Toolkit supports only the minimal built-in subset listed above. CUDA source
  gets device-side IR and PTX only, no host-side CPU assembly.
* The `nvcc` path is implemented but could not be tested on the development machine.
* The Monaco bundle makes the production JS about 3.8 MB. This is acceptable for a local tool.

## 12. Troubleshooting

| Symptom | Fix |
|---|---|
| UI: "Cannot reach the GPUForge backend" | Start uvicorn on port 8000; the Vite proxy forwards `/api` there. |
| "Clang is not available" / Compile button disabled | Set `GPUFORGE_LLVM_BIN_DIR` in `backend/.env`, restart the backend or press **Re-detect**. |
| `'stdio.h' file not found` | Windows: install VS Build Tools (C++ workload + Windows SDK). Linux: `build-essential`/`libc6-dev`. Programs without includes still work. |
| Pass features greyed out | `opt` not found. The Windows `LLVM-*.exe`/`.msi` installer omits it; use the `.tar.xz` archive. |
| PTX target disabled | Neither `nvcc` nor Clang's NVPTX backend detected (`clang -print-targets` should list `nvptx64`). |
| PTX fails with unknown CUDA identifiers | Without the CUDA Toolkit only the minimal subset is available; install the Toolkit for full headers. |
| `504 compiler_timeout` | Raise `GPUFORGE_COMPILE_TIMEOUT_S`, or simplify the program (heavy templates/headers). |
| "Pass timeline replay … approximate" | Expected occasionally; Clang and `opt` can differ in options. The level diff itself is still exact. |
