"""Phase 3 — syntax analysis: Clang's AST via ``-ast-dump=json`` (tree) and
``-ast-dump`` (raw text view)."""

import json

from app.models.responses import ASTResponse
from app.parsers.clang_ast import build_tree, filter_text_dump
from app.services.compiler_service import (
    CompileContext, command_info, first_error, run_clang, sanitize,
)

RAW_LIMIT = 400_000
# AST dumps include every declaration from #included headers (<cstdio> alone is ~13 MB of
# JSON), so allow much more output here; only main-file nodes are returned to the client.
AST_OUTPUT_LIMIT = 128 * 1024 * 1024


def analyze_ast(ctx: CompileContext) -> ASTResponse:
    res = run_clang(ctx, ["-fsyntax-only", "-Xclang", "-ast-dump=json"], max_output_bytes=AST_OUTPUT_LIMIT)
    commands = [command_info(res)]
    warnings: list[str] = []
    try:
        data = json.loads(res.stdout) if res.stdout.strip() else None
    except json.JSONDecodeError:
        data = None
        warnings.append("Clang's JSON AST output could not be parsed (possibly truncated).")

    if data is None:
        return ASTResponse(
            phase="ast", status="failed",
            message="No AST was produced. " + first_error(sanitize(ctx, res.stderr)),
            commands=commands, compiler_stderr=sanitize(ctx, res.stderr), warnings=warnings,
        )

    tree = build_tree(data, ctx.source_name)
    text_res = run_clang(ctx, ["-fsyntax-only", "-Xclang", "-ast-dump"], max_output_bytes=AST_OUTPUT_LIMIT)
    commands.append(command_info(text_res))
    raw = filter_text_dump(sanitize(ctx, text_res.stdout), ctx.source_name)
    if len(raw) > RAW_LIMIT:
        raw = raw[:RAW_LIMIT] + "\n... [truncated]"
        warnings.append("Raw AST text was truncated for display.")
    if tree["truncated"]:
        warnings.append("The AST has more nodes than the display limit; the tree is truncated.")
    if not res.ok:
        warnings.append(
            "Clang reported errors. Clang recovers from many errors and still builds a (partial) "
            "AST, which is shown here; invalid parts may be missing or marked as RecoveryExpr."
        )
    return ASTResponse(
        phase="ast",
        status="success" if res.ok else "failed",
        message=f"{tree['node_count']} AST nodes in {len(tree['nodes'])} top-level declarations from "
                f"{ctx.source_name}.",
        commands=commands,
        compiler_stderr="" if res.ok else sanitize(ctx, res.stderr),
        warnings=warnings,
        nodes=tree["nodes"],
        node_count=tree["node_count"],
        kind_counts=tree["kind_counts"],
        raw_text=raw,
        header_decls_excluded=tree["excluded"],
    )
