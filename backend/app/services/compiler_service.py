"""Shared plumbing for running Clang on user source.

Each request gets a private temp directory containing exactly one file
(``input.c`` / ``input.cpp`` / ``input.cu``). Clang is run *inside* that
directory with a relative filename, so diagnostics read ``input.c:3:5`` and
never leak server paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.errors import ToolNotAvailableError
from app.core.toolchain_detection import Toolchain, get_toolchain
from app.models.requests import SourceRequest
from app.models.responses import CommandInfo
from app.utils.source_validation import validate_source
from app.utils.subprocess_runner import ProcessResult, run_tool

SOURCE_NAMES = {"c": "input.c", "cpp": "input.cpp", "cuda": "input.cu"}

# Macros that let Clang compile the common CUDA keywords without the CUDA SDK
# headers (`-nocudainc`). They map to Clang's own CUDA attributes.
_CUDA_MINIMAL_DEFINES = [
    "-D__global__=__attribute__((global))",
    "-D__device__=__attribute__((device))",
    "-D__host__=__attribute__((host))",
    "-D__shared__=__attribute__((shared))",
    "-D__constant__=__attribute__((constant))",
    "-D__forceinline__=__inline__ __attribute__((always_inline))",
]


@dataclass
class CompileContext:
    workdir: Path
    request: SourceRequest
    toolchain: Toolchain

    @property
    def source_name(self) -> str:
        return SOURCE_NAMES[self.request.language]

    def write_source(self) -> None:
        # newline="" keeps the user's line endings so columns match the editor.
        (self.workdir / self.source_name).write_text(
            self.request.source, encoding="utf-8", newline=""
        )


def require_clang(tc: Toolchain | None = None) -> Toolchain:
    tc = tc or get_toolchain()
    if not tc.clang.available or not tc.clang.path:
        raise ToolNotAvailableError(
            "Clang is not available. " + (tc.clang.error or "") + " See README > Toolchain setup."
        )
    return tc


def prepare(req: SourceRequest, workdir: Path) -> CompileContext:
    validate_source(req.source)
    tc = require_clang()
    ctx = CompileContext(workdir=workdir, request=req, toolchain=tc)
    ctx.write_source()
    return ctx


def language_args(ctx: CompileContext) -> list[str]:
    lang = ctx.request.language
    if lang == "c":
        return ["-x", "c", "-std=c17"]
    if lang == "cpp":
        return ["-x", "c++", "-std=c++17"]
    # CUDA: always compile the *device* side, which is what PTX analysis is about.
    args = ["-x", "cuda", "--cuda-device-only", f"--cuda-gpu-arch={ctx.request.gpu_arch}"]
    if ctx.toolchain.nvcc.available and ctx.toolchain.nvcc.path:
        cuda_root = Path(ctx.toolchain.nvcc.path).resolve().parent.parent
        args += [f"--cuda-path={cuda_root}", "--no-cuda-version-check"]
    else:
        args += ["-nocudainc", "-nocudalib", *_CUDA_MINIMAL_DEFINES,
                 "-include", "__clang_cuda_builtin_vars.h"]
    return args


COMMON_DIAG_ARGS = [
    "-fno-color-diagnostics",
    "-fmessage-length=0",
    "-fdiagnostics-show-category=name",
    "-fno-caret-diagnostics",
]


def run_clang(ctx: CompileContext, args: list[str], *, max_output_bytes: int | None = None) -> ProcessResult:
    cmd = [ctx.toolchain.clang.path, *language_args(ctx), *COMMON_DIAG_ARGS, *args, ctx.source_name]
    return run_tool(cmd, cwd=ctx.workdir, max_output_bytes=max_output_bytes)


def run_opt(ctx: CompileContext, args: list[str]) -> ProcessResult:
    if not ctx.toolchain.opt.available or not ctx.toolchain.opt.path:
        raise ToolNotAvailableError("LLVM `opt` is not available; pass experiments are disabled.")
    return run_tool([ctx.toolchain.opt.path, *args], cwd=ctx.workdir)


def command_info(res: ProcessResult) -> CommandInfo:
    cmd = list(res.command)
    cmd[0] = Path(cmd[0]).stem  # show "clang", not the absolute path
    return CommandInfo(command=cmd, exit_code=res.returncode, duration_ms=round(res.duration_ms, 1))


def read_output(ctx: CompileContext, name: str) -> str:
    path = ctx.workdir / name
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return sanitize(ctx, text)


def sanitize(ctx: CompileContext, text: str) -> str:
    """Remove the server's temp-directory path from compiler output."""
    wd = str(ctx.workdir.resolve())
    # Plain, escaped (as in "C:\\x\\y" string literals) and forward-slash spellings.
    for variant, sep in ((wd.replace("\\", "\\\\"), "\\\\"), (wd, "\\"), (wd.replace("\\", "/"), "/")):
        text = text.replace(variant + sep, "").replace(variant, "<workdir>")
    return text


def first_error(stderr: str, limit: int = 3) -> str:
    errs = [ln for ln in stderr.splitlines() if ": error:" in ln or ": fatal error:" in ln]
    return "; ".join(errs[:limit]) if errs else (stderr.strip().splitlines() or ["unknown error"])[-1]
