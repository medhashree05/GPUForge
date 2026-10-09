"""Regenerate parser fixtures from the *real* installed toolchain.

    cd backend && .venv\\Scripts\\python -m tests.fixtures.regenerate

The parser unit tests run against these captured outputs so they work on
machines without Clang, while still exercising genuine compiler output.
"""

import json
from pathlib import Path

from app.core.security import request_workdir
from app.core.toolchain_detection import get_toolchain
from app.models.requests import SourceRequest
from app.services.compiler_service import prepare, read_output, run_clang

HERE = Path(__file__).parent
SAMPLES = HERE.parents[2] / "samples"


def capture(name: str, sample: str, language: str, args: list[str], *, stream: str = "file") -> None:
    req = SourceRequest(source=(SAMPLES / sample).read_text(), language=language)
    with request_workdir() as wd:
        ctx = prepare(req, wd)
        res = run_clang(ctx, [*args, "-o", "out.txt"] if stream == "file" else args)
        text = read_output(ctx, "out.txt") if stream == "file" else getattr(res, stream)
    (HERE / name).write_text(text, encoding="utf-8")
    print(f"wrote {name} ({len(text)} bytes, exit {res.returncode})")


def main() -> None:
    tc = get_toolchain()
    assert tc.clang.available, "Clang is required to regenerate fixtures"
    capture("constant_expr_O0.ll", "01_constant_expr.c", "c", ["-S", "-emit-llvm", "-O0"])
    capture("constant_expr_O2.ll", "01_constant_expr.c", "c", ["-S", "-emit-llvm", "-O2"])
    capture("loops_O0.ll", "05_loops.c", "c", ["-S", "-emit-llvm", "-O0"])
    capture("loops_O2.ll", "05_loops.c", "c", ["-S", "-emit-llvm", "-O2"])
    capture("functions_O2.s", "03_functions.c", "c",
            ["-S", "-O2", "-gline-tables-only", "-ffile-compilation-dir=.", "-masm=intel"])
    capture("constant_expr.tokens", "01_constant_expr.c", "c",
            ["-fsyntax-only", "-Xclang", "-dump-tokens"], stream="stderr")
    capture("invalid.diag", "06_invalid.c", "c", ["-fsyntax-only", "-Wall"], stream="stderr")
    capture("variables.ast.json", "02_variables.c", "c",
            ["-fsyntax-only", "-Xclang", "-ast-dump=json"], stream="stdout")
    if tc.ptx_method == "clang-nvptx":
        capture("cuda_kernel_O2.ptx", "08_cuda_kernel.cu", "cuda", ["-S", "-O2"])
    (HERE / "toolchain.json").write_text(json.dumps(
        {"clang": tc.clang.version, "triple": tc.host_triple}, indent=2))


if __name__ == "__main__":
    main()
