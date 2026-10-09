"""Phase 6 — optimization analyzer.

Two modes:

* **levels** — compile the source twice with Clang (e.g. -O0 vs -O2) and diff
  the real outputs. Additionally, to learn *which passes* changed the IR, the
  pre-optimization IR (``-Ox -Xclang -disable-llvm-passes``) is replayed through
  ``opt -passes=default<Ox> -print-changed=quiet``. The replay's result is
  compared with Clang's real output; if they differ the timeline is flagged.
* **passes** — run user-selected LLVM passes with ``opt`` on the unoptimized
  frontend IR and diff before/after.
"""

from __future__ import annotations

import re

from app.models.responses import FunctionDiff, OptimizationResponse, PassChange
from app.models.requests import OptimizationRequest
from app.parsers.ir_diff import diff_function, observe
from app.parsers.llvm_ir import Module, normalize, parse_module
from app.services.compiler_service import (
    CompileContext, command_info, first_error, read_output, run_opt, sanitize,
)
from app.services.ir_service import emit_ir

_CHANGED = re.compile(r"^\*\*\* IR Dump After (\S+) on (.+?) \*\*\*\s*$", re.MULTILINE)
PRE_OPT_FLAGS = ["-Xclang", "-disable-llvm-passes"]


def parse_pass_timeline(stderr: str) -> list[PassChange]:
    return [PassChange(pass_name=m.group(1), scope=m.group(2)) for m in _CHANGED.finditer(stderr)]


def _equivalent(a: Module, b: Module) -> bool:
    """Same instructions and block structure, ignoring value/block *names*: `opt`
    keeps names created by passes (e.g. `%.lr.ph`) while Clang discards them."""
    def shape(m: Module) -> dict:
        return {f.name: (len(f.blocks), [normalize(i.text) for i in f.instructions]) for f in m.defined}
    return shape(a) == shape(b)


def _fail(resp: OptimizationResponse, ctx: CompileContext, stderr: str, what: str) -> OptimizationResponse:
    resp.status = "failed"
    resp.message = f"{what} failed: " + first_error(sanitize(ctx, stderr))
    resp.compiler_stderr = sanitize(ctx, stderr)
    return resp


def _fill_comparison(resp: OptimizationResponse, base_ir: str, opt_ir: str) -> None:
    base, opt = parse_module(base_ir), parse_module(opt_ir)
    resp.baseline_ir, resp.optimized_ir = base_ir, opt_ir
    resp.baseline_count, resp.optimized_count = base.instruction_count, opt.instruction_count
    bc, oc = base.opcode_counts, opt.opcode_counts
    resp.opcode_delta = {op: [bc.get(op, 0), oc.get(op, 0)] for op in sorted(set(bc) | set(oc))}
    bdef = {f.name: f for f in base.defined}
    odef = {f.name: f for f in opt.defined}
    names = list(bdef) + [n for n in odef if n not in bdef]
    resp.function_diffs = [FunctionDiff(**diff_function(bdef.get(n), odef.get(n))) for n in names]
    resp.observations = observe(base, opt, resp.baseline_label, resp.optimized_label)


def analyze_optimization(ctx: CompileContext) -> OptimizationResponse:
    req = ctx.request
    if not isinstance(req, OptimizationRequest):
        req = OptimizationRequest(**req.model_dump())
    if req.passes:
        return _passes_mode(ctx, req)
    return _levels_mode(ctx, req)


def _levels_mode(ctx: CompileContext, req: OptimizationRequest) -> OptimizationResponse:
    b, o = req.baseline_level, req.optimized_level
    resp = OptimizationResponse(
        phase="optimization", status="success", mode="levels",
        baseline_label=f"-{b}", optimized_label=f"-{o}",
    )
    base_ir, r1 = emit_ir(ctx, b, out_name="opt_base.ll")
    resp.commands.append(command_info(r1))
    if not r1.ok:
        return _fail(resp, ctx, r1.stderr, f"Compiling at -{b}")
    opt_ir, r2 = emit_ir(ctx, o, out_name="opt_opt.ll")
    resp.commands.append(command_info(r2))
    if not r2.ok:
        return _fail(resp, ctx, r2.stderr, f"Compiling at -{o}")

    _fill_comparison(resp, base_ir, opt_ir)
    resp.message = (
        f"Compared real Clang output at -{b} and -{o}: {resp.baseline_count} → "
        f"{resp.optimized_count} IR instructions."
    )
    if b == o:
        resp.warnings.append("Both sides use the same optimization level; differences are not expected.")
    _attach_timeline(ctx, resp, o, opt_ir)
    return resp


def _attach_timeline(ctx: CompileContext, resp: OptimizationResponse, level: str, real_ir: str) -> None:
    if level == "O0":
        resp.pass_timeline_note = "No pass timeline: -O0 runs (almost) no optimization passes."
        return
    if not ctx.toolchain.opt.available:
        resp.pass_timeline_note = "Pass timeline unavailable: LLVM `opt` was not found."
        return
    _, r = emit_ir(ctx, level, PRE_OPT_FLAGS, out_name="pre_opt.ll")
    resp.commands.append(command_info(r))
    if not r.ok:
        resp.pass_timeline_note = "Pass timeline unavailable: could not produce pre-optimization IR."
        return
    pipeline = f"default<{level}>"
    rr = run_opt(ctx, ["-S", f"-passes={pipeline}", "-print-changed=quiet", "pre_opt.ll", "-o", "replay.ll"])
    resp.commands.append(command_info(rr))
    if not rr.ok:
        resp.pass_timeline_note = "Pass timeline unavailable: opt failed (" + first_error(rr.stderr) + ")."
        return
    resp.pass_timeline = parse_pass_timeline(rr.stderr)
    replay = parse_module(read_output(ctx, "replay.ll"))
    if _equivalent(replay, parse_module(real_ir)):
        resp.pass_timeline_note = (
            f"Reported by LLVM itself: passes from `opt -passes={pipeline} -print-changed` that changed "
            f"the IR, in order. The replay's output was verified to match Clang's -{level} IR."
        )
    else:
        resp.pass_timeline_note = (
            f"Reported by `opt -passes={pipeline} -print-changed`. Note: the replay's final IR differs "
            f"from Clang's -{level} output, so this timeline is approximate."
        )
        resp.warnings.append("Pass timeline replay did not exactly reproduce Clang's output.")


def _passes_mode(ctx: CompileContext, req: OptimizationRequest) -> OptimizationResponse:
    pipeline = ",".join(req.passes)
    resp = OptimizationResponse(
        phase="optimization", status="success", mode="passes",
        baseline_label="unoptimized IR", optimized_label=f"after {pipeline}",
    )
    # -O2 + disable-llvm-passes: IR exactly as the optimizer would receive it,
    # without the optnone/noinline markers that -O0 adds.
    base_ir, r1 = emit_ir(ctx, "O2", PRE_OPT_FLAGS, out_name="pass_base.ll")
    resp.commands.append(command_info(r1))
    if not r1.ok:
        return _fail(resp, ctx, r1.stderr, "Generating unoptimized IR")
    r2 = run_opt(ctx, ["-S", f"-passes={pipeline}", "-print-changed=quiet", "pass_base.ll", "-o", "pass_out.ll"])
    resp.commands.append(command_info(r2))
    if not r2.ok:
        return _fail(resp, ctx, r2.stderr, f"opt -passes={pipeline}")
    _fill_comparison(resp, base_ir, read_output(ctx, "pass_out.ll"))
    resp.pass_timeline = parse_pass_timeline(r2.stderr)
    resp.pass_timeline_note = "Reported by `opt -print-changed`: passes that modified the IR."
    if not resp.pass_timeline:
        resp.observations.insert(0, f"LLVM reports that `{pipeline}` did not change the IR.")
    resp.message = (
        f"Ran `opt -passes={pipeline}`: {resp.baseline_count} → {resp.optimized_count} IR instructions."
    )
    return resp
