"""Turn ``clang -Xclang -ast-dump=json`` output into a compact tree containing
only declarations written in the user's file.

Subtlety: Clang's JSON dumper omits ``file`` and ``line`` when they are the
same as in the *previously printed* location. To know which file a node is in
we therefore walk all locations in dump order and carry the last seen
file/line forward — exactly as the dumper does when writing them.
"""

from __future__ import annotations

import re
from collections import Counter

MAX_NODES = 6000


class _LocTracker:
    def __init__(self) -> None:
        self.file: str | None = None
        self.line: int | None = None

    def _bare(self, loc: dict) -> tuple[str | None, int | None, int | None]:
        if "file" in loc:
            self.file = loc["file"]
        if "line" in loc:
            self.line = loc["line"]
        return self.file, self.line, loc.get("col")

    def visit(self, loc: dict | None) -> tuple[str | None, int | None, int | None]:
        """Return (file, line, col) of the *expansion* location."""
        if not loc:
            return None, None, None
        if "spellingLoc" in loc or "expansionLoc" in loc:
            self._bare(loc.get("spellingLoc", {}))
            return self._bare(loc.get("expansionLoc", {}))
        if "offset" not in loc and "col" not in loc:
            return None, None, None
        return self._bare(loc)


def _detail(node: dict) -> str | None:
    kind = node.get("kind", "")
    if "value" in node and kind.endswith("Literal"):
        return str(node["value"])
    if "opcode" in node:
        return node["opcode"]
    if "castKind" in node:
        return node["castKind"]
    ref = node.get("referencedDecl")
    if ref and ref.get("name"):
        return f"→ {ref['name']}"
    if kind == "MemberExpr" and node.get("name"):
        return f".{node['name']}"
    return None


class _Builder:
    def __init__(self, main_file: str) -> None:
        self.main_file = main_file
        self.tracker = _LocTracker()
        self.count = 0
        self.kinds: Counter = Counter()
        self.truncated = False

    def node(self, n: dict, keep: bool) -> tuple[dict | None, str | None]:
        """Visit n (always, to keep location tracking correct); build output if keep."""
        f, line, col = self.tracker.visit(n.get("loc"))
        rng = n.get("range") or {}
        bf, bline, bcol = self.tracker.visit(rng.get("begin"))
        _, eline, _ = self.tracker.visit(rng.get("end"))
        file = f or bf
        out = None
        if keep and self.count < MAX_NODES:
            self.count += 1
            self.kinds[n.get("kind", "?")] += 1
            out = {
                "id": n.get("id", ""),
                "kind": n.get("kind", "?"),
                "name": n.get("name") or None,
                "type": (n.get("type") or {}).get("qualType"),
                "detail": _detail(n),
                "line": line if f else bline,
                "column": col if f else bcol,
                "end_line": eline,
                "implicit": bool(n.get("isImplicit")),
                "children": [],
            }
        elif keep:
            self.truncated = True
        for child in n.get("inner", []) or []:
            c, _ = self.node(child, keep)
            if out is not None and c is not None:
                out["children"].append(c)
        return out, file


def build_tree(ast: dict, main_file: str) -> dict:
    b = _Builder(main_file)
    nodes: list[dict] = []
    excluded = 0
    for decl in ast.get("inner", []) or []:
        # Decide membership from the decl's own location (visited first).
        probe = _LocTracker()
        probe.file, probe.line = b.tracker.file, b.tracker.line
        f, _, _ = probe.visit(decl.get("loc"))
        if f is None:
            f, _, _ = probe.visit((decl.get("range") or {}).get("begin"))
        keep = f == main_file and not decl.get("isImplicit")
        out, _ = b.node(decl, keep)
        if keep and out is not None:
            nodes.append(out)
        elif not keep:
            excluded += 1
    return {
        "nodes": nodes,
        "node_count": b.count,
        "kind_counts": dict(b.kinds.most_common()),
        "excluded": excluded,
        "truncated": b.truncated,
    }


# --------------------------------------------------------------- text dump
_PATH = re.compile(r"([A-Za-z]:\\[^<>,]+?|[^\s<>,:]+\.\w+):\d+:\d+")


def filter_text_dump(text: str, main_file: str) -> str:
    """Keep only top-level declarations from the user's file in ``-ast-dump`` text."""
    lines = text.splitlines()
    if not lines:
        return ""
    out = [lines[0]]
    current_file: str | None = None
    keep = False
    for line in lines[1:]:
        top = line.startswith(("|-", "`-"))
        paths = _PATH.findall(line)
        if top:
            first = paths[0] if paths else (None if "invalid sloc" in line else current_file)
            keep = first == main_file
        if paths:
            current_file = paths[-1]
        if keep:
            out.append(line)
    return "\n".join(out)
