"""Parse ``clang -Xclang -dump-tokens`` output.

Each line looks like::

    identifier 'main'      Loc=<input.c:3:5>     [LeadingSpace]
    l_paren    '('         Loc=<input.c:3:25 <Spelling=input.c:2:15>>

``-dump-tokens`` runs the *preprocessor*, so tokens coming from ``#include``d
headers appear too (they are excluded and counted), and tokens produced by
macro expansion carry a ``<Spelling=...>`` location (flagged ``from_macro``).
"""

from __future__ import annotations

import re

_LINE = re.compile(
    r"^(?P<kind>\S+)\s+'(?P<text>.*)'\s+Loc=<(?P<file>.+?):(?P<line>\d+):(?P<col>\d+)"
    r"(?P<spell>\s+<Spelling=[^>]*>)?>\s*(?P<flags>.*)$"
)
_FLAG = re.compile(r"\[(\w+)\]")
_ESCAPE = re.compile(r"\\([\\\"])")


def parse_tokens(output: str, main_file: str) -> tuple[list[dict], int, int]:
    """Return (main-file tokens, header tokens excluded, unparsed lines)."""
    tokens: list[dict] = []
    excluded = unparsed = 0
    for raw in output.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        m = _LINE.match(line)
        if not m:
            # Diagnostics (e.g. "input.c:3:1: error: ...") are interleaved on stderr.
            if not re.match(r"^\S+:\d+:\d+: (error|warning|note|fatal error)", line) and \
                    not line.endswith("generated."):
                unparsed += 1
            continue
        if m.group("file") != main_file:
            excluded += 1
            continue
        if m.group("kind") == "eof":
            continue
        tokens.append({
            "kind": m.group("kind"),
            # Clang escapes '\' and '"' when printing token spellings; undo that.
            "text": _ESCAPE.sub(r"\1", m.group("text")),
            "line": int(m.group("line")),
            "column": int(m.group("col")),
            "flags": _FLAG.findall(m.group("flags")),
            "from_macro": m.group("spell") is not None,
        })
    return tokens, excluded, unparsed
