"""Full pipeline orchestration and the metrics report (Phase 9).

Every metric is derived from a phase result produced in the same request.
When a phase did not succeed its metric is ``None`` ("Unavailable") — never
an estimate.
"""

from __future__ import annotations

from typing import Callable

from app.core.errors import CompilerTimeoutError, ToolExecutionError, ToolNotAvailableError
from app.models.requests import OptimizationRequest
from app.models.responses import (
    ASTResponse, AssemblyResponse, DiagnosticsResponse, FullAnalysisResponse, IRResponse, Metric,
    MetricsResponse, OptimizationResponse, PhaseResponse, PTXResponse, TokensResponse,
)
from app.services.assembly_service import generate_assembly
from app.services.ast_service import analyze_ast
from app.services.compiler_service import CompileContext
from app.services.diagnostics_service import analyze_diagnostics
from app.services.ir_service import generate_ir
from app.services.optimization_service import analyze_optimization
from app.services.ptx_service import generate_ptx
from app.services.token_service import analyze_tokens


def _safe(model: type[PhaseResponse], phase: str, fn: Callable[[], PhaseResponse]) -> PhaseResponse:
    """Run one phase; convert tool problems into a phase-level status instead of a crash."""
    try:
        return fn()
    except ToolNotAvailableError as exc:
        return model(phase=phase, status="unsupported", message=exc.message)
    except (CompilerTimeoutError, ToolExecutionError) as exc:
        return model(phase=phase, status="failed", message=exc.message)


def _skipped(model: type[PhaseResponse], phase: str) -> PhaseResponse:
    return model(
        phase=phase, status="skipped",
        message="Not attempted: the source has errors (see Diagnostics). Code generation requires "
                "a program that passes semantic analysis.",
    )


def run_full(ctx: CompileContext) -> FullAnalysisResponse:
    tokens = _safe(TokensResponse, "tokens", lambda: analyze_tokens(ctx))
    ast = _safe(ASTResponse, "ast", lambda: analyze_ast(ctx))
    diags = _safe(DiagnosticsResponse, "diagnostics", lambda: analyze_diagnostics(ctx))
    if diags.status == "success":
        ir = _safe(IRResponse, "ir", lambda: generate_ir(ctx))
        opt_ctx = CompileContext(ctx.workdir, OptimizationRequest(**ctx.request.model_dump()), ctx.toolchain)
        opt = _safe(OptimizationResponse, "optimization", lambda: analyze_optimization(opt_ctx))
        asm = _safe(AssemblyResponse, "assembly", lambda: generate_assembly(ctx))
        ptx = _safe(PTXResponse, "ptx", lambda: generate_ptx(ctx))
    else:
        ir = _skipped(IRResponse, "ir")
        opt = _skipped(OptimizationResponse, "optimization")
        asm = _skipped(AssemblyResponse, "assembly")
        # For non-CUDA input or a missing toolchain, "unsupported" is more accurate than "skipped".
        if ctx.request.language != "cuda" or ctx.toolchain.ptx_method is None:
            ptx = generate_ptx(ctx)  # returns "unsupported" without invoking a compiler
        else:
            ptx = _skipped(PTXResponse, "ptx")
    metrics = build_metrics(ctx, tokens, ast, diags, ir, opt, asm, ptx)
    return FullAnalysisResponse(tokens=tokens, ast=ast, diagnostics=diags, ir=ir,
                                optimization=opt, assembly=asm, ptx=ptx, metrics=metrics)


def _ok(p: PhaseResponse) -> bool:
    return p.status == "success"


def build_metrics(ctx, tokens, ast, diags, ir, opt, asm, ptx) -> MetricsResponse:
    tc, req = ctx.toolchain, ctx.request
    level = req.opt_level
    lines = req.source.splitlines()
    m: list[Metric] = [
        Metric(key="source_lines", label="Source lines", value=len(lines),
               definition="Number of lines in the submitted source, including blank and comment lines."),
        Metric(key="source_loc", label="Non-blank source lines", value=sum(1 for ln in lines if ln.strip()),
               definition="Lines containing at least one non-whitespace character.",
               limitation="Comment-only lines are counted."),
        Metric(key="tokens", label="Tokens", value=tokens.token_count if tokens.token_count else None,
               definition="Tokens Clang's preprocessor produced from the main file (after macro expansion).",
               limitation="Tokens from #include'd headers are excluded; macro expansions are counted per use."),
        Metric(key="ast_nodes", label="AST nodes", value=ast.node_count if ast.node_count else None,
               definition="Nodes in Clang's AST for declarations written in the main file.",
               limitation="Includes implicit nodes Clang inserts (e.g. ImplicitCastExpr); header declarations excluded."),
        Metric(key="errors", label="Errors", value=diags.error_count if diags.status in ("success", "failed") else None,
               definition="Diagnostics with severity error/fatal error from clang -fsyntax-only."),
        Metric(key="warnings", label="Warnings", value=diags.warning_count if diags.status in ("success", "failed") else None,
               definition="Diagnostics with severity warning (with -Wall -Wextra)."),
        Metric(key="ir_instructions", label=f"LLVM IR instructions (-{level})",
               value=ir.instruction_count if _ok(ir) else None,
               definition="Instructions inside function definitions in the .ll output (labels, comments, declarations excluded).",
               limitation="A static count; one IR instruction can become zero or many machine instructions."),
        Metric(key="ir_O_baseline", label=f"IR instructions {opt.baseline_label or '(baseline)'}",
               value=opt.baseline_count if _ok(opt) else None,
               definition="IR instruction count of the optimizer comparison's baseline."),
        Metric(key="ir_O_optimized", label=f"IR instructions {opt.optimized_label or '(optimized)'}",
               value=opt.optimized_count if _ok(opt) else None,
               definition="IR instruction count after optimization.",
               limitation="Fewer instructions usually, but not always, means faster code (e.g. inlining/unrolling grow code)."),
        Metric(key="asm_instructions", label=f"{tc.host_arch or 'CPU'} assembly instructions (-{level})",
               value=asm.instruction_count if _ok(asm) else None,
               definition="Machine instructions in the .s output (directives, labels, comments excluded).",
               limitation=f"Specific to {tc.host_triple}; not comparable with PTX or other architectures."),
        Metric(key="ptx_instructions", label=f"PTX instructions ({req.gpu_arch}, -{level})",
               value=ptx.summary.instruction_count if _ok(ptx) and ptx.summary else None,
               definition="PTX statements inside function bodies (directives, labels excluded).",
               limitation="PTX is a virtual ISA; ptxas translates it to SASS, so this is not the final GPU instruction count."),
        Metric(key="ptx_memory_ops", label="PTX memory operations",
               value=sum(ptx.summary.memory_ops.values()) if _ok(ptx) and ptx.summary else None,
               definition="ld/st/atom/red instructions in PTX, all state spaces."),
        Metric(key="ir_compile_ms", label=f"IR generation time (-{level})",
               value=ir.commands[0].duration_ms if _ok(ir) and ir.commands else None, unit="ms",
               definition="Wall-clock time of one `clang -S -emit-llvm` process, measured by the backend.",
               limitation="Compilation time, not program execution time. Includes process start-up; single sample, noisy."),
        Metric(key="compiler", label="Compiler", value=tc.clang.version,
               definition="Clang version that produced every output."),
        Metric(key="target", label="Host target", value=tc.host_triple,
               definition="Default target triple for CPU outputs."),
        Metric(key="compiled", label="Compilation result",
               value="success" if _ok(ir) else ("failed" if diags.status == "failed" or ir.status == "failed" else None),
               definition="Whether Clang generated LLVM IR for the program (exit code 0)."),
    ]
    return MetricsResponse(phase="metrics", status="success", message="Metrics derived from this run.", metrics=m)
