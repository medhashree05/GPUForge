"""Parse Clang's text diagnostics produced with
``-fno-caret-diagnostics -fdiagnostics-show-category=name``::

    input.c:8:13: error: use of undeclared identifier 'x' [Semantic Issue]
    input.c:10:11: error: incompatible ... [-Wint-conversion,Value Conversion Issue]

The bracketed category ("Parse Issue", "Semantic Issue", "Lexical or
Preprocessor Issue", ...) comes from Clang itself — GPUForge does not guess it.
"""

from __future__ import annotations

import re

_DIAG = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+): (?P<sev>fatal error|error|warning|note|remark): "
    r"(?P<msg>.*?)(?: \[(?P<tags>[^\]]+)\])?$"
)
_NOLOC = re.compile(r"^(?P<file>[^:]+): (?P<sev>fatal error|error|warning|note|remark): (?P<msg>.*)$")


def parse_diagnostics(stderr: str, main_file: str, source: str) -> list[dict]:
    src_lines = source.splitlines()
    out: list[dict] = []
    for raw in stderr.splitlines():
        line = raw.rstrip()
        m = _DIAG.match(line)
        if m:
            flag = category = None
            if m.group("tags"):
                for tag in (t.strip() for t in m.group("tags").split(",")):
                    if tag.startswith("-W"):
                        flag = tag
                    else:
                        category = tag
            ln, in_main = int(m.group("line")), m.group("file") == main_file
            snippet = src_lines[ln - 1] if in_main and 0 < ln <= len(src_lines) else None
            out.append({
                "severity": m.group("sev"),
                "message": m.group("msg"),
                "line": ln if in_main else None,
                "column": int(m.group("col")) if in_main else None,
                "category": category,
                "flag": flag,
                "in_main_file": in_main,
                "snippet": snippet,
            })
            continue
        m = _NOLOC.match(line)
        if m and not line.startswith(("clang", "In file")):
            out.append({
                "severity": m.group("sev"), "message": m.group("msg"), "line": None,
                "column": None, "category": None, "flag": None,
                "in_main_file": m.group("file") == main_file, "snippet": None,
            })
    return out
