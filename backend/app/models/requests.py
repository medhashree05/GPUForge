from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.security import ALLOWED_GPU_ARCHS, ALLOWED_PASSES

Language = Literal["c", "cpp", "cuda"]
OptLevel = Literal["O0", "O1", "O2", "O3", "Os", "Oz"]
Target = Literal["cpu", "ptx"]


class SourceRequest(BaseModel):
    source: str = Field(..., description="C, C++ or CUDA source code")
    language: Language = "c"
    opt_level: OptLevel = "O0"
    target: Target = "cpu"
    gpu_arch: str = "sm_75"

    @field_validator("gpu_arch")
    @classmethod
    def _arch(cls, v: str) -> str:
        if v not in ALLOWED_GPU_ARCHS:
            raise ValueError(f"gpu_arch must be one of {ALLOWED_GPU_ARCHS}")
        return v


class OptimizationRequest(SourceRequest):
    baseline_level: OptLevel = "O0"
    optimized_level: OptLevel = "O2"
    # When non-empty, run these LLVM passes (in order) with `opt` instead of
    # comparing two clang optimization levels.
    passes: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("passes")
    @classmethod
    def _passes(cls, v: list[str]) -> list[str]:
        bad = [p for p in v if p not in ALLOWED_PASSES]
        if bad:
            raise ValueError(f"Unknown or disallowed passes: {bad}")
        return v


class AssemblyRequest(SourceRequest):
    intel_syntax: bool = True


class PTXRequest(SourceRequest):
    compare_opt_level: OptLevel | None = None
