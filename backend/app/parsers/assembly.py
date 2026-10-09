"""Parse target assembly produced by ``clang -S``.

Counting method: after removing comments, a line is counted as an
*instruction* when it is non-empty, does not start with ``.`` (assembler
directive), is not a label (``name:``), and is not a symbol assignment
(``sym = value``). Prologue/epilogue instructions *are* real instructions and
are counted; directives, labels and debug info are not.

Source mapping uses the line-table directives Clang emits with
``-gline-tables-only``: ``.loc <file> <line> <col>`` (DWARF/ELF/Mach-O) or
``.cv_loc <func> <file> <line> <col>`` (CodeView/Windows). Each instruction is
attributed to the most recent such directive. If none are present, no mapping
is reported.
"""

from __future__ import annotations

import re
from collections import Counter

_LOC = re.compile(r"^\s*\.loc\s+(\d+)\s+(\d+)")
_CVLOC = re.compile(r"^\s*\.cv_loc\s+\d+\s+(\d+)\s+(\d+)")
_LABEL = re.compile(r"^\s*([\w.$@?]+|\"[^\"]+\"):")
_ASSIGN = re.compile(r"^\s*[\w.$@]+\s*=\s*")
_INTERNAL_LABEL = re.compile(r"^(\.?L(tmp|func_|loh|_|section|cfi|set|debug|info|line|names|str)|@feat|\$)")


def comment_markers(arch: str | None) -> tuple[str, ...]:
    if arch and arch.startswith(("aarch64", "arm64")):
        return ("//", ";")
    if arch and arch.startswith("arm"):
        return ("@", "//")
    return ("#", ";")


def _strip_comment(line: str, markers: tuple[str, ...]) -> str:
    cut = len(line)
    for m in markers:
        i = line.find(m)
        if i != -1:
            cut = min(cut, i)
    return line[:cut].rstrip()


def analyze_assembly(asm: str, arch: str | None, main_file_id: str = "1") -> dict:
    markers = comment_markers(arch)
    filtered: list[str] = []
    source_map: list[dict] = []
    mnemonics: Counter = Counter()
    current_src: int | None = None

    for raw in asm.splitlines():
        m = _LOC.match(raw)
        if m:
            current_src = int(m.group(2)) if m.group(1) == main_file_id else None
            continue
        m = _CVLOC.match(raw)
        if m:
            current_src = int(m.group(2)) if m.group(1) == main_file_id else None
            continue
        code = _strip_comment(raw, markers)
        stripped = code.strip()
        if not stripped:
            continue
        # Labels first: block labels such as `.LBB0_1:` also start with '.'.
        lm = _LABEL.match(stripped)
        if lm and stripped.endswith(":"):
            # Keep function names and basic-block labels (jump targets); hide
            # bookkeeping labels used only by debug/unwind info.
            if not _INTERNAL_LABEL.match(lm.group(1)):
                filtered.append(stripped)
            continue
        if stripped.startswith(".") or _ASSIGN.match(stripped):
            continue
        mnemonic = stripped.split(None, 1)[0].lower()
        mnemonics[mnemonic] += 1
        filtered.append("    " + raw.strip())
        if current_src is not None:
            source_map.append({"asm_line": len(filtered), "source_line": current_src})

    return {
        "filtered": "\n".join(filtered),
        "instruction_count": sum(mnemonics.values()),
        "mnemonic_counts": dict(mnemonics.most_common()),
        "source_map": source_map,
    }
