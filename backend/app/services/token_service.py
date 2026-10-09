"""Phase 2 — lexical analysis via ``clang -fsyntax-only -Xclang -dump-tokens``."""

from collections import Counter

from app.models.responses import TokensResponse
from app.parsers.clang_tokens import parse_tokens
from app.services.compiler_service import CompileContext, command_info, run_clang, sanitize


def analyze_tokens(ctx: CompileContext) -> TokensResponse:
    res = run_clang(ctx, ["-fsyntax-only", "-Xclang", "-dump-tokens"])
    # Tokens are printed to stderr together with any diagnostics.
    tokens, excluded, unparsed = parse_tokens(res.stderr, ctx.source_name)
    warnings = []
    if unparsed:
        warnings.append(f"{unparsed} line(s) of token output could not be parsed and were skipped.")
    if res.truncated:
        warnings.append("Token output exceeded the size limit and was truncated.")
    if not res.ok:
        warnings.append(
            "Clang reported errors while preprocessing/parsing. Tokens produced before analysis "
            "stopped are still shown; see Diagnostics for the errors."
        )
    status = "success" if tokens else "failed"
    return TokensResponse(
        phase="tokens",
        status=status,
        message=(
            f"{len(tokens)} tokens in {ctx.source_name} (after preprocessing; header tokens excluded)."
            if tokens else "No tokens were produced."
        ),
        commands=[command_info(res)],
        # stderr mixes token lines with diagnostics; keep only the diagnostics.
        compiler_stderr="" if res.ok else sanitize(
            ctx, "\n".join(ln for ln in res.stderr.splitlines() if "Loc=<" not in ln)
        ),
        warnings=warnings,
        tokens=tokens,
        token_count=len(tokens),
        kind_counts=dict(Counter(t["kind"] for t in tokens).most_common()),
        header_tokens_excluded=excluded,
    )
