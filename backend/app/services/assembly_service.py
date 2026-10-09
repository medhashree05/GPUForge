"""Phase 7 — host CPU assembly via ``clang -S``.

``-gline-tables-only`` is added so the assembly contains line-table
directives used for source mapping (debug info does not change the generated
instructions). Directives are hidden in the filtered view.
"""

from __future__ import annotations

from app.models.responses import AsmVariant, AssemblyResponse
from app.models.requests import AssemblyRequest
from app.parsers.assembly import analyze_assembly
from app.parsers.explanations import AARCH64, X86
from app.services.compiler_service import (
    CompileContext, command_info, first_error, read_output, run_clang, sanitize,
)
from app.services.ir_service import explain

COUNTING_METHOD = (
    "Counts lines that are machine instructions: comments, assembler directives (lines starting "
    "with '.'), labels ('name:') and symbol assignments are excluded. Prologue/epilogue "
    "instructions are real instructions and are included. This is a static count of the code, "
    "not the number of instructions executed."
)


def _syntax_args(arch: str | None, intel: bool) -> list[str]:
    return ["-masm=intel"] if intel and arch in ("x86_64", "i386", "i686", "x86") else []


def _compile(ctx: CompileContext, level: str, intel: bool, out: str):
    arch = ctx.toolchain.host_arch
    res = run_clang(ctx, ["-S", f"-{level}", "-gline-tables-only", "-ffile-compilation-dir=.",
                          *_syntax_args(arch, intel), "-o", out])
    return (read_output(ctx, out) if res.ok else ""), res


def generate_assembly(ctx: CompileContext, compare_levels: tuple[str, ...] = ("O0", "O2")) -> AssemblyResponse:
    req = ctx.request
    intel = req.intel_syntax if isinstance(req, AssemblyRequest) else True
    arch, triple = ctx.toolchain.host_arch, ctx.toolchain.host_triple
    if req.language == "cuda":
        return AssemblyResponse(
            phase="assembly", status="unsupported", arch=arch, target_triple=triple,
            message="CPU assembly is not generated for CUDA source: GPUForge compiles only the "
                    "device side of .cu files. See the PTX phase for GPU code.",
        )
    level = req.opt_level
    asm, res = _compile(ctx, level, intel, f"out_{level}.s")
    if not res.ok:
        return AssemblyResponse(
            phase="assembly", status="failed", arch=arch, target_triple=triple, opt_level=level,
            message="Assembly generation failed: " + first_error(sanitize(ctx, res.stderr)),
            commands=[command_info(res)], compiler_stderr=sanitize(ctx, res.stderr),
        )
    a = analyze_assembly(asm, arch)
    resp = AssemblyResponse(
        phase="assembly", status="success",
        message=f"{a['instruction_count']} {arch} instructions at -{level} (target {triple}).",
        commands=[command_info(res)], compiler_stderr=sanitize(ctx, res.stderr),
        asm=asm, filtered_asm=a["filtered"], target_triple=triple, arch=arch, opt_level=level,
        instruction_count=a["instruction_count"], mnemonic_counts=a["mnemonic_counts"],
        counting_method=COUNTING_METHOD, source_map=a["source_map"],
        explanations=explain(a["mnemonic_counts"], AARCH64 if arch and arch.startswith(("aarch64", "arm64")) else X86),
    )
    if not a["source_map"]:
        resp.warnings.append("No line-table directives were found, so no source mapping is shown.")
    resp.comparison.append(AsmVariant(opt_level=level, instruction_count=a["instruction_count"],
                                      mnemonic_counts=a["mnemonic_counts"]))
    for lv in compare_levels:
        if lv == level:
            continue
        other, r = _compile(ctx, lv, intel, f"out_{lv}.s")
        resp.commands.append(command_info(r))
        if r.ok:
            b = analyze_assembly(other, arch)
            resp.comparison.append(AsmVariant(opt_level=lv, instruction_count=b["instruction_count"],
                                              mnemonic_counts=b["mnemonic_counts"]))
    resp.comparison.sort(key=lambda v: v.opt_level)
    return resp
