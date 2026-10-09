"""Phase 5 — LLVM IR generation with ``clang -S -emit-llvm``."""

from __future__ import annotations

from app.models.responses import InstructionExplanation, IRFunction, IRResponse
from app.parsers.explanations import LLVM_IR
from app.parsers.llvm_ir import Module, parse_module
from app.services.compiler_service import (
    CompileContext, command_info, first_error, read_output, run_clang, sanitize,
)
from app.utils.subprocess_runner import ProcessResult


def emit_ir(ctx: CompileContext, level: str, extra: list[str] | None = None,
            out_name: str | None = None) -> tuple[str, ProcessResult]:
    out = out_name or f"ir_{level}.ll"
    res = run_clang(ctx, ["-S", "-emit-llvm", f"-{level}", *(extra or []), "-o", out])
    return (read_output(ctx, out) if res.ok else ""), res


def explain(counts: dict[str, int], table: dict[str, str]) -> list[InstructionExplanation]:
    return [
        InstructionExplanation(opcode=op, count=n, explanation=table[op])
        for op, n in sorted(counts.items(), key=lambda kv: -kv[1]) if op in table
    ]


def functions_of(mod: Module) -> list[IRFunction]:
    return [
        IRFunction(name=f.name, instruction_count=len(f.instructions), block_count=len(f.blocks),
                   is_declaration=f.is_declaration)
        for f in mod.functions.values()
    ]


def generate_ir(ctx: CompileContext, level: str | None = None) -> IRResponse:
    level = level or ctx.request.opt_level
    ir, res = emit_ir(ctx, level)
    if not res.ok:
        return IRResponse(
            phase="ir", status="failed", opt_level=level,
            message="IR generation failed: " + first_error(sanitize(ctx, res.stderr)),
            commands=[command_info(res)], compiler_stderr=sanitize(ctx, res.stderr),
        )
    mod = parse_module(ir)
    counts = dict(mod.opcode_counts.most_common())
    warnings = []
    if level == "O0":
        warnings.append(
            "At -O0 Clang marks functions `optnone noinline`, so running `opt` on this IR would "
            "not optimize it. The optimizer view uses a separate, unmarked baseline."
        )
    if ctx.request.language == "cuda":
        warnings.append("This is the CUDA *device-side* IR (target nvptx64), not host code.")
    return IRResponse(
        phase="ir",
        status="success",
        message=f"{mod.instruction_count} instructions in {len(mod.defined)} defined function(s) at -{level}.",
        commands=[command_info(res)],
        compiler_stderr=sanitize(ctx, res.stderr),
        warnings=warnings,
        ir=ir,
        opt_level=level,
        target_triple=mod.target_triple,
        instruction_count=mod.instruction_count,
        opcode_counts=counts,
        functions=functions_of(mod),
        explanations=explain(counts, LLVM_IR),
    )
