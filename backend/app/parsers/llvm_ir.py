"""A lightweight structural parser for textual LLVM IR (.ll).

It is *not* a full IR parser: it recognises functions, basic blocks and
instructions well enough to count and diff them.

Counting method: an *instruction* is any non-empty line inside a function body
(`define ... { ... }`) that is not a basic-block label, a comment, or a debug
record (`#dbg_...`). The opcode is the first word after an optional
``%result =`` prefix, ignoring ``tail``/``musttail``/``notail`` call markers.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

_DEFINE = re.compile(r"^define\b.*?@(\"[^\"]+\"|[-\w$.]+)\s*\(")
_DECLARE = re.compile(r"^declare\b.*?@(\"[^\"]+\"|[-\w$.]+)\s*\(")
_LABEL = re.compile(r"^([-\w$.]+|\"[^\"]+\"):(\s*;.*)?$")
_ASSIGN = re.compile(r"^%[-\w$.\"]+\s*=\s*")
_CALL_PREFIX = re.compile(r"^(tail|musttail|notail)\s+")
_CALLEE = re.compile(r"\bcall\b.*?@(\"[^\"]+\"|[-\w$.]+)\s*\(")
_TRIPLE = re.compile(r'^target triple\s*=\s*"([^"]+)"', re.MULTILINE)


@dataclass
class Instruction:
    text: str          # original text (stripped)
    opcode: str
    block: str


@dataclass
class Function:
    name: str
    instructions: list[Instruction] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    body_lines: list[str] = field(default_factory=list)  # labels + instructions, in order
    is_declaration: bool = False

    @property
    def opcode_counts(self) -> Counter:
        return Counter(i.opcode for i in self.instructions)

    def callees(self) -> Counter:
        out: Counter = Counter()
        for ins in self.instructions:
            if ins.opcode in ("call", "invoke"):
                m = _CALLEE.search(ins.text) or re.search(r"@(\"[^\"]+\"|[-\w$.]+)\s*\(", ins.text)
                if m:
                    out[m.group(1).strip('"')] += 1
        return out


@dataclass
class Module:
    functions: dict[str, Function]
    target_triple: str | None

    @property
    def defined(self) -> list[Function]:
        return [f for f in self.functions.values() if not f.is_declaration]

    @property
    def instruction_count(self) -> int:
        return sum(len(f.instructions) for f in self.defined)

    @property
    def opcode_counts(self) -> Counter:
        total: Counter = Counter()
        for f in self.defined:
            total.update(f.opcode_counts)
        return total


def opcode_of(line: str) -> str:
    s = _ASSIGN.sub("", line.strip())
    s = _CALL_PREFIX.sub("", s)
    return s.split(None, 1)[0].rstrip(",") if s else ""


def parse_module(text: str) -> Module:
    functions: dict[str, Function] = {}
    current: Function | None = None
    block = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if current is None:
            m = _DEFINE.match(line)
            if m:
                current = Function(name=m.group(1).strip('"'))
                block = "entry"
                if line.endswith("}"):  # one-line definition (rare)
                    functions[current.name] = current
                    current = None
                continue
            m = _DECLARE.match(line)
            if m:
                name = m.group(1).strip('"')
                functions.setdefault(name, Function(name=name, is_declaration=True))
            continue

        stripped = line.strip()
        if stripped == "}":
            functions[current.name] = current
            current = None
            continue
        if not stripped or stripped.startswith(";"):
            continue
        if not raw.startswith((" ", "\t")):
            m = _LABEL.match(stripped)
            if m:
                block = m.group(1)
                current.blocks.append(block)
                current.body_lines.append(f"{block}:")
                continue
        if stripped.startswith("#dbg_"):
            continue
        if not current.blocks:
            current.blocks.append(block)
        current.instructions.append(Instruction(stripped, opcode_of(stripped), block))
        current.body_lines.append("  " + stripped)

    m = _TRIPLE.search(text)
    return Module(functions=functions, target_triple=m.group(1) if m else None)


# ------------------------------------------------------------- normalisation
_METADATA = re.compile(r",\s*![-\w.]+\s+!\d+")          # , !tbaa !5   , !llvm.loop !9
_ATTR_GROUP = re.compile(r"\s#\d+\b")
_LOCAL = re.compile(r"%[-\w$.]+|%\"[^\"]+\"")


def normalize(line: str) -> str:
    """Make two IR lines comparable when only SSA names / metadata differ."""
    s = _METADATA.sub("", line.strip())
    s = _ATTR_GROUP.sub("", s)
    s = _LOCAL.sub("%_", s)
    if s.endswith(":") or re.match(r"^[-\w$.]+:", s):
        return "<label>:"
    return re.sub(r"\s+", " ", s)
