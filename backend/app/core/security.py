"""Per-request isolation helpers and allow-lists for user-selectable options.

Users never supply raw compiler flags. They choose from the enumerations below,
and GPUForge translates the choice into fixed argument lists.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import get_settings

# LLVM new-pass-manager pass names the user may run individually through `opt`.
ALLOWED_PASSES: dict[str, str] = {
    "mem2reg": "Promote stack slots (alloca/load/store) to SSA registers",
    "sroa": "Scalar replacement of aggregates; also promotes allocas",
    "instcombine": "Combine/simplify instructions (algebraic simplification, folding)",
    "simplifycfg": "Simplify the control-flow graph (merge/remove blocks, fold branches)",
    "sccp": "Sparse conditional constant propagation",
    "early-cse": "Early common-subexpression elimination",
    "gvn": "Global value numbering (redundancy elimination)",
    "dce": "Dead code elimination",
    "adce": "Aggressive dead code elimination",
    "dse": "Dead store elimination",
    "reassociate": "Reassociate expressions to expose constant folding",
    "licm": "Loop-invariant code motion",
    "loop-rotate": "Rotate loops into do-while form",
    "indvars": "Canonicalize induction variables",
    "loop-unroll": "Unroll loops",
    "inline": "Inline function calls",
    "globaldce": "Remove unused global functions/variables",
    "tailcallelim": "Tail-call elimination",
}

ALLOWED_GPU_ARCHS = ["sm_50", "sm_60", "sm_70", "sm_75", "sm_80", "sm_86", "sm_89", "sm_90"]


@contextmanager
def request_workdir() -> Iterator[Path]:
    """A fresh private temporary directory, always removed afterwards."""
    root = get_settings().work_root
    path = Path(tempfile.mkdtemp(prefix="gpuforge_", dir=root))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
