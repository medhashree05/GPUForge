import json

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.security import ALLOWED_GPU_ARCHS, ALLOWED_PASSES
from app.core.toolchain_detection import Toolchain, get_toolchain, refresh
from app.models.responses import Sample, ToolchainResponse, ToolStatus

router = APIRouter(tags=["toolchain"])


def to_response(tc: Toolchain) -> ToolchainResponse:
    clang_ok = tc.clang.available
    opt_ok = clang_ok and tc.opt.available
    # Only offer passes that this `opt` build reports in `--print-passes`.
    passes = {k: v for k, v in ALLOWED_PASSES.items() if k in tc.opt_passes} if opt_ok else {}
    return ToolchainResponse(
        clang=ToolStatus(**vars(tc.clang)),
        opt=ToolStatus(**vars(tc.opt)),
        nvcc=ToolStatus(**vars(tc.nvcc)),
        host_triple=tc.host_triple,
        host_arch=tc.host_arch,
        nvptx_backend=tc.nvptx_backend,
        system_headers=tc.system_headers,
        system_headers_error=tc.system_headers_error,
        ptx_method=tc.ptx_method,
        capabilities={
            "tokens": clang_ok, "ast": clang_ok, "diagnostics": clang_ok, "ir": clang_ok,
            "optimization": clang_ok, "pass_timeline": opt_ok, "individual_passes": opt_ok,
            "assembly": clang_ok, "ptx": tc.ptx_method is not None,
        },
        notes=tc.notes,
        allowed_passes=passes,
        allowed_gpu_archs=ALLOWED_GPU_ARCHS,
    )


@router.get("/toolchain", response_model=ToolchainResponse)
def toolchain() -> ToolchainResponse:
    return to_response(get_toolchain())


@router.post("/toolchain/refresh", response_model=ToolchainResponse)
def toolchain_refresh() -> ToolchainResponse:
    return to_response(refresh())


@router.get("/samples", response_model=list[Sample])
def samples() -> list[Sample]:
    d = get_settings().samples_dir
    manifest = json.loads((d / "samples.json").read_text(encoding="utf-8"))
    return [
        Sample(id=s["id"], title=s["title"], language=s["language"], description=s["description"],
               source=(d / s["file"]).read_text(encoding="utf-8"))
        for s in manifest
    ]
