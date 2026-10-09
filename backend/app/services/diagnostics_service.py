"""Phase 4 — semantic analysis: Clang's own diagnostics from ``-fsyntax-only``
(preprocess + parse + semantic checks, no code generation)."""

from app.models.responses import DiagnosticsResponse
from app.parsers.clang_diagnostics import parse_diagnostics
from app.services.compiler_service import CompileContext, command_info, run_clang, sanitize


def analyze_diagnostics(ctx: CompileContext) -> DiagnosticsResponse:
    res = run_clang(ctx, ["-fsyntax-only", "-Wall", "-Wextra"])
    stderr = sanitize(ctx, res.stderr)
    diags = parse_diagnostics(stderr, ctx.source_name, ctx.request.source)
    errors = sum(1 for d in diags if d["severity"] in ("error", "fatal error"))
    warns = sum(1 for d in diags if d["severity"] == "warning")
    warnings = []
    if not res.ok and errors == 0:
        warnings.append("Clang failed but no error lines could be parsed; see raw compiler output.")
    if res.ok:
        msg = "Parsing and semantic analysis succeeded" + (f" with {warns} warning(s)." if warns else ".")
    else:
        msg = f"Clang reported {errors} error(s) and {warns} warning(s)."
    return DiagnosticsResponse(
        phase="diagnostics",
        status="success" if res.ok else "failed",
        message=msg,
        commands=[command_info(res)],
        compiler_stderr=stderr,
        warnings=warnings,
        diagnostics=diags,
        error_count=errors,
        warning_count=warns,
        semantic_ok=res.ok,
    )
