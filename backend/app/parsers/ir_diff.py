"""Compare two LLVM IR modules and describe *observed* differences.

Design rule: every observation must be backed by numbers computed from the two
outputs. We never claim which optimization pass caused a change; at most we say
a change is "consistent with" a well-known transformation. Pass attribution is
only reported when it comes from LLVM itself (``opt -print-changed``).
"""

from __future__ import annotations

import difflib
import re
from collections import Counter

from app.parsers.llvm_ir import Function, Module, normalize

MEMORY_OPS = {"alloca", "load", "store"}
ARITH_OPS = {
    "add", "sub", "mul", "sdiv", "udiv", "srem", "urem", "shl", "lshr", "ashr",
    "and", "or", "xor", "fadd", "fsub", "fmul", "fdiv", "frem", "fneg",
}
_CONST_RET = re.compile(r"^ret\s+\S+\s+(-?\d+|true|false|0x[0-9A-Fa-f]+|[-+]?\d+\.\d+(e[-+]?\d+)?)$")
_VECTOR = re.compile(r"<\s*\d+\s+x\s+")


def diff_function(a: Function | None, b: Function | None) -> dict:
    """Instruction-level diff on normalised lines; returns original text for display."""
    a_lines = a.body_lines if a else []
    b_lines = b.body_lines if b else []
    sm = difflib.SequenceMatcher(
        a=[normalize(x) for x in a_lines], b=[normalize(x) for x in b_lines], autojunk=False
    )
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += [{"op": "equal", "text": b_lines[j]} for j in range(j1, j2)]
        else:
            out += [{"op": "removed", "text": a_lines[i]} for i in range(i1, i2)]
            out += [{"op": "added", "text": b_lines[j]} for j in range(j1, j2)]
    if a is None:
        status = "added"
    elif b is None:
        status = "removed"
    elif all(d["op"] == "equal" for d in out):
        status = "unchanged"
    else:
        status = "changed"
    return {
        "name": (a or b).name,
        "status": status,
        "baseline_count": len(a.instructions) if a else 0,
        "optimized_count": len(b.instructions) if b else 0,
        "lines": out,
    }


def _sum(c: Counter, keys: set[str]) -> int:
    return sum(v for k, v in c.items() if k in keys)


def observe(base: Module, opt: Module, base_label: str, opt_label: str) -> list[str]:
    obs: list[str] = []
    bdef = {f.name: f for f in base.defined}
    odef = {f.name: f for f in opt.defined}

    bt, ot = base.instruction_count, opt.instruction_count
    if bt == ot and all(
        diff_function(bdef.get(n), odef.get(n))["status"] == "unchanged" for n in set(bdef) | set(odef)
    ):
        return [f"The IR instructions are identical (after renaming) between {base_label} and {opt_label}."]
    if bt:
        pct = (ot - bt) / bt * 100
        obs.append(
            f"Total instructions in defined functions: {bt} ({base_label}) → {ot} ({opt_label}), "
            f"{pct:+.0f}%."
        )

    removed = sorted(set(bdef) - set(odef))
    added = sorted(set(odef) - set(bdef))
    if removed:
        obs.append(
            "Function definitions no longer present after optimization: "
            + ", ".join(f"`{n}`" for n in removed)
            + ". (Typically unused internal functions are deleted, e.g. after their calls were inlined.)"
        )
    if added:
        obs.append("New function definitions appeared: " + ", ".join(f"`{n}`" for n in added) + ".")

    for name in sorted(set(bdef) & set(odef)):
        obs += _observe_function(bdef[name], odef[name])

    if not any(_VECTOR.search(i.text) for f in base.defined for i in f.instructions) and any(
        _VECTOR.search(i.text) for f in opt.defined for i in f.instructions
    ):
        obs.append(
            "Vector-typed instructions (e.g. `<4 x i32>`) appear only in the optimized IR, "
            "which is consistent with loop or SLP vectorization."
        )
    return obs


def _observe_function(a: Function, b: Function) -> list[str]:
    obs: list[str] = []
    ac, bc = a.opcode_counts, b.opcode_counts
    n = f"`{a.name}`"
    if ac == bc and len(a.blocks) == len(b.blocks):
        d = diff_function(a, b)
        if d["status"] == "unchanged":
            return []

    am, bm = _sum(ac, MEMORY_OPS), _sum(bc, MEMORY_OPS)
    if ac["alloca"] and not bc["alloca"]:
        obs.append(
            f"In {n}: all {ac['alloca']} `alloca` stack slots were eliminated and memory operations "
            f"(alloca/load/store) went from {am} to {bm}. Values are kept in SSA registers instead "
            "(consistent with mem2reg/SROA promotion)."
        )
    elif am != bm:
        obs.append(f"In {n}: memory operations (alloca/load/store) changed from {am} to {bm}.")

    aa, ba = _sum(ac, ARITH_OPS), _sum(bc, ARITH_OPS)
    rets = [i.text for i in b.instructions if i.opcode == "ret"]
    if len(b.instructions) == 1 and rets and _CONST_RET.match(rets[0]) and aa > 0:
        obs.append(
            f"In {n}: the optimized body is the single instruction `{rets[0]}`. The baseline "
            f"performed {aa} arithmetic instruction(s); the result was computed at compile time "
            "(constant folding / propagation)."
        )
    elif aa != ba:
        obs.append(f"In {n}: arithmetic instructions changed from {aa} to {ba}.")

    if len(a.blocks) != len(b.blocks) or ac["br"] != bc["br"]:
        obs.append(
            f"In {n}: basic blocks {len(a.blocks)} → {len(b.blocks)}, branch instructions "
            f"(`br`) {ac['br']} → {bc['br']}"
            + (", i.e. control flow was simplified." if len(b.blocks) < len(a.blocks) else ".")
        )
    if ac["icmp"] + ac["fcmp"] != bc["icmp"] + bc["fcmp"]:
        obs.append(
            f"In {n}: comparisons (`icmp`/`fcmp`) {ac['icmp'] + ac['fcmp']} → {bc['icmp'] + bc['fcmp']}."
        )

    acall, bcall = a.callees(), b.callees()
    for callee in sorted(acall):
        if acall[callee] and bcall[callee] < acall[callee] and not callee.startswith("llvm."):
            obs.append(
                f"In {n}: calls to `{callee}` went from {acall[callee]} to {bcall[callee]} "
                "(the callee's code was inlined or the call was found unnecessary)."
            )
    if bc["phi"] > ac["phi"]:
        obs.append(
            f"In {n}: {bc['phi'] - ac['phi']} `phi` node(s) appeared. A phi selects a value depending "
            "on which predecessor block was executed; they replace stack variables written in several places."
        )
    if bc["select"] > ac["select"] and bc["br"] < ac["br"]:
        obs.append(
            f"In {n}: `select` instructions increased ({ac['select']} → {bc['select']}) while branches "
            "decreased, consistent with converting a branch into a branch-free select."
        )
    return obs
