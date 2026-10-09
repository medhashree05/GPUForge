# GPUForge interview guide

Everything quoted below is real output from this project's toolchain: Clang/LLVM 23.1.3,
`x86_64-pc-windows-msvc`, NVPTX `sm_75`. Re-run the samples to reproduce it; other compiler
versions may differ, which is why GPUForge never hard-codes results.

---

## 1. 60-second explanation

"GPUForge is a web tool that shows what a real compiler does to your code, phase by phase. You
type C, C++ or CUDA. The backend runs Clang and LLVM and collects the token stream, the AST,
semantic diagnostics, LLVM IR, optimized IR, x86 assembly and NVIDIA PTX. The interesting part is
the analysis layer I wrote. It parses each output format, diffs IR between optimization levels,
and reports only changes it can prove from the outputs. It also asks LLVM which passes changed the
IR and checks that answer against Clang's real `-O2` output. It maps assembly back to source lines
and classifies PTX instructions by type and memory space. I didn't write a compiler. I built the
tooling that makes a production compiler explainable, with a hardened subprocess layer, because
it's compiling untrusted code."

## 2. Two-minute architecture explanation

- **Frontend (React, TypeScript, Vite, Tailwind).** A Monaco editor, a React Flow pipeline
  diagram, and one view per phase. A single `POST /api/analyze/full` returns every phase, so tabs
  switch instantly and all views describe the same compile. The optimization and PTX views can
  issue follow-up requests (other levels, individual passes).
- **Backend (FastAPI, Pydantic).** Three layers:
  1. `api/`: routes and validated request models (language, opt level, pass and GPU-arch
     allow-lists).
  2. `services/`: one per phase. Each writes the source into a **private temp directory**, runs
     Clang with a **fixed argument list**, and builds a typed response with a `status` of
     success, failed, unsupported or skipped. The exact commands are included in the response.
  3. `parsers/`: pure functions from compiler text to data, unit-tested on captured real output.
- **Process layer.** One `run_tool` function: `shell=False`, timeout, output cap.
- **Toolchain detection** runs each tool once at startup, and the UI enables features from the
  resulting capabilities. With no CUDA installed, PTX automatically comes from Clang's NVPTX
  backend.

## 3. Pipeline diagram

```
            ┌────────────── Clang frontend ──────────────┐   ┌──── LLVM ────┐   ┌──── back ends ────┐
 source ──► │ preprocess+lex ─► parse ─► Sema (types)    │──►│ IR ─► passes │──►│ x86-64 asm        │
            │  -dump-tokens     -ast-dump  diagnostics   │   │ -emit-llvm   │   │ NVPTX → PTX       │
            └────────────────────────────────────────────┘   │ opt -passes  │   │ (ptxas → SASS,    │
                                                             └──────────────┘   │  not by GPUForge) │
 GPUForge: token parser · AST walker · diag parser · IR parser+differ · asm filter+mapper · PTX parser
```

Clang actually parses and runs Sema together (it type-checks as it parses), so the diagram is an
educational view, not a claim of strictly separate passes.

## 4. Each compiler phase in this project

| Phase | What happens | Evidence from GPUForge |
|---|---|---|
| Lexing | Characters become tokens; the preprocessor expands macros. | `int x = 10 + 20;` → `int`, `identifier 'x'`, `equal`, `numeric_constant '10'`, `plus`, … `return x + ;` tokenizes fine but fails parsing (integration test). |
| Parsing / AST | Grammar check; builds the AST. | `FunctionDecl main` → `CompoundStmt` → `DeclStmt` → `VarDecl x` → `BinaryOperator '+'`; Clang adds `ImplicitCastExpr <LValueToRValue>` nodes that are not in the source. |
| Semantic analysis | Types, declarations, calls. | `06_invalid.c`: `expected ';'` is a **Parse Issue**; `undeclared_var` and `too few arguments` are **Semantic Issue**; `char *p = 42` is **Value Conversion Issue** `[-Wint-conversion]`. |
| IR generation | AST → SSA LLVM IR. | At `-O0` every local is an `alloca` with `store`/`load`. |
| Optimization | IR → better IR. | `-O2`: `main` becomes `ret i32 55`. |
| Code generation | IR → target assembly or PTX. | `-O2` `sum_of_squares` → `imul ecx,ecx; imul edx,edx; lea eax,[rdx+rcx]; ret`. |

## 5. Why Clang and LLVM

- Production quality: the same frontend and optimizer used by real toolchains, so the outputs
  are the real thing.
- Every phase is exposed through flags (`-dump-tokens`, `-ast-dump=json`, `-emit-llvm`,
  `opt -print-changed`, `-S`), so no C++ plugin or library linking is needed.
- One toolchain covers CPU **and** NVIDIA GPU (the NVPTX back end), which is what made PTX possible
  without the CUDA Toolkit.
- Stable, documented textual formats (LLVM IR, Clang diagnostics) make reliable parsers feasible.

## 6. Why not Flex/Bison + a custom AST

A toy compiler shows that I can write a grammar. Its output says nothing about how real
compilers behave: no real C semantics, no real optimizer, no real code generation. GPUForge works
on **real C/C++/CUDA with real compiler output**, so the questions it answers ("why did
`-O2` delete my loop?") are questions engineers actually ask. The engineering challenges are
also different and more realistic: parsing evolving tool formats, matching outputs fairly,
process isolation, and not over-claiming.

## 7. LLVM IR vs. assembly vs. PTX

| | LLVM IR | CPU assembly | PTX |
|---|---|---|---|
| Level | Target-independent IR, SSA, infinite virtual registers | Real ISA of one CPU (here x86-64) | **Virtual** ISA for NVIDIA GPUs |
| Registers | `%1, %2, …` (unlimited) | Fixed (`eax`, `rsp`, …) | Unlimited virtual (`%r<10>`, `%rd<8>`, `%p<2>`) declared with `.reg` |
| Memory | Typed pointers, `alloca` | Stack/heap addressing | Explicit **state spaces**: `ld.global`, `ld.shared`, `ld.param` |
| Next step | Back end | Assembler → machine code | `ptxas` / driver → SASS (real GPU machine code) |

Observed: saxpy PTX reads `threadIdx.x` as `mov.u32 %r6, %tid.x` and computes the index with
`mad.lo.s32`; `__syncthreads()` became `bar.sync 0`.

## 8. Optimization-level comparisons and their limits

Observed `-O0 → -O2` (IR instructions in defined functions):

| Sample | -O0 → -O2 | What the outputs show |
|---|---|---|
| constant_expr | 11 → 1 | `main` = `ret i32 55`. **Note:** even at `-O0` Clang's frontend already wrote `store i32 30`, so `10 + 20` was folded before LLVM ran; `x * 2 - 5` was left for the optimizer. |
| redundant | `work`: 29 → 3 | `shl i32 %0, 3` + `add 21` + `ret`. The unused variable, duplicate `a*4`, `a - a` and the `if (1 > 2)` block are gone; `4a + 4a` became `a << 3`. |
| conditionals | `classify`: 18 → 2 | The if/else chain became one call to the intrinsic `@llvm.scmp.i32.i32` (three-way signed compare); blocks 7 → 1. |
| loops | `sum_to`: 22 → 17 | The loop was **replaced by a closed-form formula** (`smax`, `mul i33`, `lshr`). Arithmetic instructions *increased* (2 → 8) but no loop remains: fewer instructions ≠ faster, and here more instructions = O(1) instead of O(n). |
| functions | 20 → 5 | `square` inlined and deleted; `main` = `ret i32 25`. |

The pass timeline (LLVM's own report) for `redundant` was: SROA → EarlyCSE → … → InstCombine →
CorrelatedValuePropagation → Reassociate → InstCombine → Inliner.

**Limits:** these are static counts; the diff is textual after normalizing names; pass attribution
comes only from `opt -print-changed`, and the observations deliberately say "consistent with".

## 9. CPU vs. GPU compilation

- A CPU back end optimizes a single thread: register allocation onto few registers, instruction
  selection and scheduling.
- A CUDA kernel is written for **one thread**. Thousands run it, using `threadIdx`/`blockIdx` to
  pick their data. PTX makes the memory hierarchy explicit (global, shared, local, param).
- Observed: at `-O0` the CUDA sample has 42 *generic* memory operations and 0 global; at `-O2` it
  has 0 generic and 5 global + 5 shared. The optimizer proved which address space each pointer
  belongs to (`cvta.to.global`), which matters on real hardware because generic addressing needs
  extra work.
- Branching matters more on GPUs (warp divergence). GPUForge counts branches statically but makes
  no performance claims without benchmarking.

## 10. Toolchain and OS interactions

- **Windows:** Clang targets `x86_64-pc-windows-msvc` and uses MSVC's headers and the Windows SDK,
  which it finds automatically. Debug line info is CodeView (`.cv_loc`), not DWARF (`.loc`), so
  the mapper supports both.
- **Packaging:** the Windows LLVM installer lacks `opt`; the release archive includes it.
- **Path leaks:** CodeView embeds the compilation directory, so the raw assembly contained the
  temp-dir path, escaped several times over. Fixed with `-ffile-compilation-dir=.` instead of
  string scrubbing.
- **CUDA without the Toolkit:** `-nocudainc -nocudalib` plus Clang's own builtin-vars header and
  attribute macros.

## 11. Security and subprocess handling

User source is untrusted. The safeguards:

- **No shell:** argument lists only.
- **Fixed executables:** no user-controlled flags; enumerations and allow-lists only.
- **Limits:** timeout and output cap; 64 KiB source limit and a body-size check before JSON parsing.
- **Isolation:** per-request temp dir, always deleted.
- **No file reading:** quoted `#include`, `#embed`, macro includes and path traversal are blocked,
  because Clang would print file contents in its diagnostics.
- **Nothing executes:** compilation only.
- **No internals leak:** no stack traces sent to clients.

It is honestly **not a sandbox**: for multi-user deployment it would need containers or VMs with
CPU, memory and network limits.

## 12. Real bugs encountered and fixed

1. **Wrong pass timeline:** replaying `opt` on `-O0` IR failed to inline because Clang marks `-O0`
   functions `optnone noinline`. Fix: replay on `-O2 -Xclang -disable-llvm-passes` IR. The replay
   is now verified against Clang's output on every request.
2. **Replay "mismatch" that wasn't one:** `opt` keeps value names that passes create
   (`%.lr.ph`), while Clang discards them. Fix: compare instruction shape and block structure,
   ignoring names.
3. **Truncated AST:** `<cstdio>` produced about 13 MB of JSON, more than the 8 MB output cap, so
   the JSON was invalid. Fix: per-call output limits.
4. **AST nodes assigned to the wrong file:** Clang's JSON omits unchanged `file`/`line` fields.
   Fix: track locations in dump order.
5. **Temp path leak** in CodeView build info → `-ffile-compilation-dir=.`.
6. **Jump-target labels hidden** (`.LBB0_1:` treated as a directive). Caught by a unit test.
7. **`cvta` counted as a memory access:** it is an address conversion. Reclassified.
8. **UI highlight lost** when Monaco mounted after the effect ran. Fix: editor instance kept in
   state.
9. **Test leakage:** Testing Library auto-cleanup isn't registered without Vitest globals.

## 13. Twenty interview questions

1. **What does GPUForge implement versus Clang?** Clang/LLVM do all compilation. I implemented the
   parsers for six output formats, the IR differ and observation rules, the pass-timeline replay
   and check, assembly and PTX analysis, the hardened process layer, the API and the UI.
2. **How do you know which pass made a change?** I don't infer it. I replay the real `-O2` pipeline
   with `opt -print-changed=quiet`, which prints a header for each pass that changed the IR. I
   check the replay ends with the same IR as Clang's `-O2` (`_equivalent` in
   `optimization_service.py`); if it doesn't, the timeline is labelled approximate.
3. **Why not replay on `-O0` IR?** It's marked `optnone`/`noinline`. I hit this: the inliner never
   ran.
4. **How does the IR diff work?** It parses functions into labels and instructions, normalizes SSA
   names, metadata and attribute groups, then runs `difflib.SequenceMatcher` per function and
   shows the original text.
5. **Limitations of that diff?** It is textual. A reordered or renamed instruction can show as
   removed plus added, and it has no data-flow understanding.
6. **What's SSA, and why does `-O2` IR have `phi`?** Each value is assigned once. When a variable
   has different values on different control-flow paths, a `phi` picks the right one; mem2reg/SROA
   introduce them when promoting `alloca`s.
7. **Why so many `alloca`/`load`/`store` at `-O0`?** Clang emits every local as a stack slot (simple
   and debuggable); the optimizer promotes them to registers. The observation rule reports this
   only when all `alloca`s disappear.
8. **Is the AST a parse tree?** No. A concrete parse tree mirrors the grammar, including
   punctuation. Clang's AST keeps semantic structure and adds implicit nodes (casts) that aren't
   in the text.
9. **Can tokenization succeed on an invalid program?** Yes; `return x + ;` is valid tokens and
   tested.
10. **How do you tell parse errors from semantic errors?** Clang's own
    `-fdiagnostics-show-category=name`: "Parse Issue" versus "Semantic Issue". I don't guess.
11. **How is assembly mapped to source?** `-gline-tables-only` makes Clang emit line directives
    (`.cv_loc` on Windows, `.loc` elsewhere). Each instruction is attributed to the latest
    directive. No directives means no mapping is shown.
12. **How do you count assembly instructions?** Comments, directives, labels and assignments are
    excluded; prologue and epilogue are included. It's documented in the API response.
13. **Does fewer instructions mean faster?** No. `sum_to` gained arithmetic instructions but lost
    its loop. Static counts are also not dynamic counts.
14. **What is PTX, and how do you get it without CUDA?** NVIDIA's virtual ISA. Clang's NVPTX back
    end compiles `.cu` device code with `--cuda-device-only -nocudainc`; `nvcc -ptx` is used
    when installed. No GPU is needed.
15. **What does your PTX analysis tell you?** Kernels (`.entry`), parameters, `.reg` declarations,
    instruction classes and memory state spaces. For example `-O2` turned 42 generic accesses into
    global and shared ones.
16. **How do you stop someone reading `/etc/passwd`?** Quoted, computed, `#embed` and traversal
    includes are rejected (after line-splice removal), only `<system>` headers are allowed, there
    is no shell, and each request runs in its own temp dir.
17. **Is a timeout a sandbox?** No. It bounds time only. Real isolation needs OS mechanisms; this
    is documented.
18. **How do you test parsers without Clang in CI?** Fixtures are captured from real Clang by
    `tests/fixtures/regenerate.py`. Integration tests skip automatically without Clang.
19. **How do you handle a missing tool?** Detection marks capabilities. Endpoints return 503 or
    `unsupported`, the UI disables the control and explains why, and no placeholder output is
    ever produced (tested).
20. **What would you add next?** Use-def-aware IR diffing (LLVM's Python bindings or `llvm-diff`),
    `ptxas -v` resource usage (registers, shared memory) when the CUDA Toolkit is present,
    `llvm-mca` throughput estimates clearly labelled as models, and container isolation.

## 14. Limitations and future extensions

**Limitations:** static counts only; textual IR diff; pass attribution only through replay;
minimal CUDA subset without the Toolkit; the `nvcc` path is untested here; single-user local
security model; the AST view is capped at 6000 nodes.

**Extensions:**
- `ptxas -v` / `cuobjdump -sass` for real GPU resource usage and SASS.
- `llvm-mca` for CPU throughput modelling (labelled as a model).
- `opt -print-changed=diff` to show each pass's own diff step by step.
- A Godbolt-style per-line color mapping across IR, assembly and PTX.
- Sandboxing (containers, seccomp, cgroups) for multi-user deployment.
- Optional, explicitly enabled and isolated benchmarking on a real GPU.
