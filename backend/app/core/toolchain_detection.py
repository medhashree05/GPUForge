"""Discover which compiler tools exist *and actually work* on this machine.

Nothing is assumed: every tool is located, then executed once with a harmless
argument (``--version`` etc.). Results are cached until ``refresh()`` is called.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import CompilerTimeoutError, ToolExecutionError
from app.core.security import request_workdir
from app.utils.subprocess_runner import run_tool

EXE = ".exe" if sys.platform == "win32" else ""


@dataclass
class ToolInfo:
    name: str
    path: str | None = None
    available: bool = False
    version: str | None = None
    error: str | None = None


@dataclass
class Toolchain:
    clang: ToolInfo
    opt: ToolInfo
    nvcc: ToolInfo
    host_triple: str | None = None
    host_arch: str | None = None
    llvm_targets: list[str] = field(default_factory=list)
    nvptx_backend: bool = False
    system_headers: bool = False
    system_headers_error: str | None = None
    ptx_method: str | None = None  # "nvcc" | "clang-nvptx" | None
    opt_passes: set[str] = field(default_factory=set)  # from `opt --print-passes`
    notes: list[str] = field(default_factory=list)


def _candidate(tool: str, explicit: str | None) -> str | None:
    settings = get_settings()
    if explicit:
        return explicit if Path(explicit).is_file() else None
    if settings.llvm_bin_dir:
        p = Path(settings.llvm_bin_dir) / f"{tool}{EXE}"
        if p.is_file():
            return str(p)
    found = shutil.which(tool)
    if found:
        return found
    if sys.platform == "win32":
        default = Path(r"C:\Program Files\LLVM\bin") / f"{tool}{EXE}"
        if default.is_file():
            return str(default)
    return None


def _nvcc_candidate() -> str | None:
    settings = get_settings()
    if settings.nvcc_path:
        return settings.nvcc_path if Path(settings.nvcc_path).is_file() else None
    found = shutil.which("nvcc")
    if found:
        return found
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        p = Path(cuda_path) / "bin" / f"nvcc{EXE}"
        if p.is_file():
            return str(p)
    return None


def _probe(name: str, path: str | None, args: list[str]) -> ToolInfo:
    info = ToolInfo(name=name, path=path)
    if not path:
        info.error = f"{name} was not found (set GPUFORGE_LLVM_BIN_DIR or add it to PATH)."
        return info
    try:
        res = run_tool([path, *args], timeout_s=15)
    except (ToolExecutionError, CompilerTimeoutError) as exc:
        info.error = exc.message
        return info
    text = (res.stdout or res.stderr).strip()
    if res.returncode != 0:
        info.error = f"{name} {' '.join(args)} exited with code {res.returncode}"
        return info
    info.available = True
    info.version = next((ln.strip() for ln in text.splitlines() if "version" in ln.lower()), text[:120])
    return info


def _detect() -> Toolchain:
    settings = get_settings()
    clang = _probe("clang", _candidate("clang", settings.clang_path), ["--version"])
    opt = _probe("opt", _candidate("opt", settings.opt_path), ["--version"])
    nvcc = _probe("nvcc", _nvcc_candidate(), ["--version"])
    tc = Toolchain(clang=clang, opt=opt, nvcc=nvcc)

    if clang.available:
        res = run_tool([clang.path, "-print-target-triple"], timeout_s=15)
        if res.ok:
            tc.host_triple = res.stdout.strip()
            tc.host_arch = tc.host_triple.split("-")[0]
        res = run_tool([clang.path, "-print-targets"], timeout_s=15)
        if res.ok:
            tc.llvm_targets = [
                ln.split()[0] for ln in res.stdout.splitlines()[1:] if ln.strip() and " - " in ln
            ]
            tc.nvptx_backend = "nvptx64" in tc.llvm_targets
        tc.system_headers, tc.system_headers_error = _probe_headers(clang.path)
        if not tc.system_headers:
            tc.notes.append(
                "Clang works but standard headers (e.g. <stdio.h>) were not found. Programs "
                "without #include still work. On Windows install the MSVC Build Tools + "
                "Windows SDK; on Linux install libc development headers."
            )
    if opt.available:
        res = run_tool([opt.path, "--print-passes"], timeout_s=15)
        if res.ok:
            # Lines look like "  instcombine<...>" or "  mem2reg"; keep the bare names.
            tc.opt_passes = {ln.strip().split("<", 1)[0] for ln in res.stdout.splitlines()
                             if ln.startswith("  ")}
    else:
        tc.notes.append("`opt` not found: individual LLVM pass experiments are disabled.")

    if nvcc.available:
        tc.ptx_method = "nvcc"
    elif clang.available and tc.nvptx_backend:
        tc.ptx_method = "clang-nvptx"
        tc.notes.append(
            "nvcc not found: PTX is produced by Clang's NVPTX backend without CUDA SDK headers "
            "(minimal built-in CUDA subset only)."
        )
    else:
        tc.notes.append("No PTX toolchain (nvcc or Clang with NVPTX) was found; PTX phase disabled.")
    return tc


def _probe_headers(clang: str) -> tuple[bool, str | None]:
    with request_workdir() as wd:
        src = wd / "probe.c"
        src.write_text("#include <stdio.h>\nint main(void){return 0;}\n")
        try:
            res = run_tool([clang, "-fsyntax-only", str(src)], cwd=wd, timeout_s=30)
        except (ToolExecutionError, CompilerTimeoutError) as exc:
            return False, exc.message
    if res.ok:
        return True, None
    first = next((ln for ln in res.stderr.splitlines() if "error" in ln), res.stderr[:200])
    return False, first.replace(str(src), "probe.c")


_lock = threading.Lock()
_cached: Toolchain | None = None


def get_toolchain() -> Toolchain:
    global _cached
    with _lock:
        if _cached is None:
            _cached = _detect()
        return _cached


def refresh() -> Toolchain:
    global _cached
    with _lock:
        _cached = _detect()
        return _cached


def set_toolchain_for_tests(tc: Toolchain | None) -> None:
    global _cached
    with _lock:
        _cached = tc
