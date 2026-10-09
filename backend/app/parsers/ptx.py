"""Static parser for PTX text (NVIDIA's virtual ISA).

Counting method: an *instruction* is a statement inside a function body
(``{ ... }``) that ends with ``;`` and does not start with ``.`` (directives
such as ``.reg``/``.shared``) or ``//``. Labels (``$L__BB0_2:``) are skipped.
Predicate guards (``@%p1``/``@!%p1``) are removed before reading the opcode.

These are *static* counts of the code, not dynamic counts of what executes —
a loop body appears once regardless of trip count. They say nothing direct
about runtime performance.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

_FUNC = re.compile(r"^\s*(?:\.visible\s+|\.extern\s+|\.weak\s+)*\.(entry|func)\s+(?:\([^)]*\)\s*)?([\w$]+)")
_PARAM = re.compile(r"\.param\s+([^,)]+?)\s*(?:,|\)|$)")
_PRED = re.compile(r"^@!?%\w+\s+")
_VERSION = re.compile(r"^\.version\s+(\S+)", re.MULTILINE)
_TARGET = re.compile(r"^\.target\s+(.+)$", re.MULTILINE)

MEMORY_BASES = {"ld", "ldu", "st", "atom", "red", "prefetch", "cp"}
STATE_SPACES = {"global", "shared", "local", "param", "const", "generic"}
CONTROL = {"bra", "brx", "call", "ret", "exit", "trap"}
SYNC = {"bar", "barrier", "membar", "fence"}
COMPARE = {"setp", "selp", "set", "slct"}
CONVERT = {"cvt", "cvta"}  # cvta converts addresses between state spaces; it does not access memory
MOVE = {"mov"}
ARITH = {
    "add", "sub", "mul", "mad", "fma", "div", "rem", "abs", "neg", "min", "max",
    "shl", "shr", "and", "or", "xor", "not", "rcp", "sqrt", "rsqrt", "sin", "cos",
    "lg2", "ex2", "popc", "clz", "brev", "bfe", "bfi", "mul24", "mad24", "sad", "copysign",
}


@dataclass
class PTXFunction:
    name: str
    is_kernel: bool
    params: list[str] = field(default_factory=list)
    opcodes: list[str] = field(default_factory=list)
    reg_decls: list[str] = field(default_factory=list)


@dataclass
class PTXModule:
    version: str | None
    target: str | None
    functions: list[PTXFunction]

    @property
    def opcodes(self) -> list[str]:
        return [op for f in self.functions for op in f.opcodes]


def classify(opcode: str) -> str:
    base = opcode.split(".", 1)[0]
    if base in MEMORY_BASES:
        return "memory"
    if base in CONTROL:
        return "control"
    if base in SYNC:
        return "sync"
    if base in COMPARE:
        return "compare/select"
    if base in CONVERT:
        return "conversion"
    if base in MOVE:
        return "move"
    if base in ARITH:
        return "arithmetic"
    return "other"


def memory_space(opcode: str) -> str | None:
    parts = opcode.split(".")
    if parts[0] not in MEMORY_BASES:
        return None
    for p in parts[1:]:
        if p in STATE_SPACES:
            return p
    return "generic"


def parse_ptx(text: str) -> PTXModule:
    functions: list[PTXFunction] = []
    current: PTXFunction | None = None
    in_header = in_body = False
    depth = 0
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if current is None:
            m = _FUNC.match(line)
            if m:
                current = PTXFunction(name=m.group(2), is_kernel=m.group(1) == "entry")
                in_header = True
                current.params += _PARAM.findall(line.split("(", 1)[-1]) if "(" in line else []
                if line.endswith(";"):  # forward declaration only
                    current = None
                    in_header = False
            continue
        if in_header:
            if line.startswith(".param"):
                current.params += _PARAM.findall(line)
            if line.startswith("{"):
                in_header, in_body, depth = False, True, 1
            elif line.endswith(";"):  # prototype ended without body
                current, in_header = None, False
            continue
        if in_body:
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                functions.append(current)
                current, in_body = None, False
                continue
            if line in ("{", "}") or line.endswith(":"):
                continue
            if line.startswith(".reg"):
                current.reg_decls.append(line.rstrip(";"))
                continue
            if line.startswith(".") or not line.endswith(";"):
                continue
            stmt = _PRED.sub("", line)
            opcode = stmt.split(None, 1)[0].rstrip(";")
            current.opcodes.append(opcode)

    v = _VERSION.search(text)
    t = _TARGET.search(text)
    return PTXModule(
        version=v.group(1) if v else None,
        target=t.group(1).strip() if t else None,
        functions=functions,
    )


def summarize(mod: PTXModule) -> dict:
    ops = mod.opcodes
    classes = Counter(classify(o) for o in ops)
    mem = Counter(s for s in (memory_space(o) for o in ops) if s)
    branch = sum(1 for o in ops if o.split(".", 1)[0] in ("bra", "brx"))
    # Group full opcodes by their first two components (e.g. ld.global) for readability.
    grouped = Counter(".".join(o.split(".")[:2]) if o.split(".")[0] in MEMORY_BASES else o.split(".")[0] for o in ops)
    return {
        "instruction_count": len(ops),
        "class_counts": dict(classes.most_common()),
        "opcode_counts": dict(grouped.most_common()),
        "memory_ops": dict(mem.most_common()),
        "branch_count": branch,
    }
