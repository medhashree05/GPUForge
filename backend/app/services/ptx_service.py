"""Phase 8 — NVIDIA PTX generation and static analysis.

Toolchain preference: ``nvcc -ptx`` (NVIDIA's compiler) when installed, else
Clang's NVPTX backend (``clang -x cuda --cuda-device-only -S``). Neither needs
a GPU: PTX generation is pure compilation. GPUForge never executes kernels.
"""

from __future__ import annotations

from collections import Counter

from app.models.requests import PTXRequest
from app.models.responses import PTXFunction, PTXResponse, PTXSummary
from app.parsers.explanations import PTX
from app.parsers.ptx import parse_ptx, summarize
from app.services.compiler_service import (
    CompileContext, command_info, first_error, read_output, run_clang, sanitize,
)
from app.services.ir_service import explain
from app.utils.subprocess_runner import run_tool

NO_PERF_CLAIM = (
    "Static instruction counts describe the generated code, not execution speed. Performance "
    "depends on occupancy, memory access patterns and the final SASS produced by ptxas; it can "
    "only be established by benchmarking on a GPU."
)


def _compile(ctx: CompileContext, level: str, out: str):
    tc = ctx.toolchain
    if tc.ptx_method == "nvcc":
        cmd = [tc.nvcc.path, "-ptx", f"-arch={ctx.request.gpu_arch}", ctx.source_name, "-o", out]
        if level == "O0":
            cmd.insert(1, "-G")  # device debug build = no device optimization
        res = run_tool(cmd, cwd=ctx.workdir)
    else:
        res = run_clang(ctx, ["-S", f"-{level}", "-o", out])
    return (read_output(ctx, out) if res.ok else ""), res


def _summary(ptx: str, level: str) -> PTXSummary:
    return PTXSummary(opt_level=level, **summarize(parse_ptx(ptx)))


def generate_ptx(ctx: CompileContext) -> PTXResponse:
    req = ctx.request
    tc = ctx.toolchain
    base = PTXResponse(phase="ptx", status="unsupported", gpu_arch=req.gpu_arch, method=tc.ptx_method)
    if tc.ptx_method is None:
        base.message = ("No PTX toolchain found: install the CUDA Toolkit (nvcc) or an LLVM build with "
                        "the NVPTX target. All CPU-side phases remain available.")
        return base
    if req.language != "cuda":
        base.message = "PTX is generated from CUDA source. Select the CUDA language (e.g. the CUDA sample)."
        return base

    level = req.opt_level
    ptx, res = _compile(ctx, level, "out.ptx")
    base.commands.append(command_info(res))
    if not res.ok:
        base.status = "failed"
        base.message = "PTX generation failed: " + first_error(sanitize(ctx, res.stderr))
        base.compiler_stderr = sanitize(ctx, res.stderr)
        if tc.ptx_method == "clang-nvptx":
            base.warnings.append(
                "Without the CUDA Toolkit, only a minimal CUDA subset is available (__global__, "
                "__device__, __shared__, threadIdx/blockIdx/blockDim/gridDim, __syncthreads, "
                "atomics builtins). CUDA runtime headers and libraries are not included."
            )
        return base

    mod = parse_ptx(ptx)
    summary = _summary(ptx, level)
    base.status = "success"
    base.ptx = ptx
    base.ptx_version, base.target = mod.version, mod.target
    base.functions = [
        PTXFunction(name=f.name, is_kernel=f.is_kernel, instruction_count=len(f.opcodes), params=f.params)
        for f in mod.functions
    ]
    base.register_decls = sorted({d for f in mod.functions for d in f.reg_decls})
    base.summary = summary
    kernels = sum(1 for f in mod.functions if f.is_kernel)
    tool = "nvcc" if tc.ptx_method == "nvcc" else "Clang NVPTX backend"
    base.message = (f"{tool}: {kernels} kernel entry point(s), {summary.instruction_count} PTX "
                    f"instructions for {req.gpu_arch} at -{level}.")
    base.warnings.append(NO_PERF_CLAIM)
    if tc.ptx_method == "nvcc" and level not in ("O0",):
        base.warnings.append("nvcc controls device optimization itself; only -O0 (mapped to -G) changes it.")
    by_base: Counter = Counter()
    for op, n in summary.opcode_counts.items():
        by_base[op.split(".")[0]] += n
    base.explanations = explain(dict(by_base), PTX)

    cmp_level = req.compare_opt_level if isinstance(req, PTXRequest) else None
    if cmp_level and cmp_level != level:
        other, r2 = _compile(ctx, cmp_level, "cmp.ptx")
        base.commands.append(command_info(r2))
        if r2.ok:
            base.comparison = _summary(other, cmp_level)
        else:
            base.warnings.append(f"Comparison compile at -{cmp_level} failed.")
    return base
