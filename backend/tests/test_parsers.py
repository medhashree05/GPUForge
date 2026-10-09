"""Parser unit tests against real Clang output captured in tests/fixtures
(regenerate with `python -m tests.fixtures.regenerate`)."""

import json

from app.parsers.assembly import analyze_assembly
from app.parsers.clang_ast import build_tree
from app.parsers.clang_diagnostics import parse_diagnostics
from app.parsers.clang_tokens import parse_tokens
from app.parsers.ir_diff import diff_function, observe
from app.parsers.llvm_ir import normalize, opcode_of, parse_module
from app.parsers.ptx import classify, memory_space, parse_ptx, summarize
from tests.conftest import SAMPLES, fixture_text


# ------------------------------------------------------------------ tokens
def test_tokens_from_real_dump():
    tokens, excluded, unparsed = parse_tokens(fixture_text("constant_expr.tokens"), "input.c")
    assert unparsed == 0 and excluded == 0
    assert [t["kind"] for t in tokens[:3]] == ["int", "identifier", "l_paren"]
    main = next(t for t in tokens if t["text"] == "main")
    assert (main["line"], main["column"]) == (3, 5)
    nums = [t["text"] for t in tokens if t["kind"] == "numeric_constant"]
    assert nums == ["10", "20", "2", "5"]


def test_tokens_macro_and_header_lines():
    out = (
        "int 'int'\t Loc=<input.c:3:1>  [StartOfLine]\n"
        "l_paren '(' Loc=<input.c:3:25 <Spelling=input.c:2:15>> [LeadingSpace]\n"
        "identifier 'printf' Loc=<C:\\SDK\\stdio.h:10:5>\n"
        "string_literal '\\\"%d\\\"' Loc=<input.c:4:1>\n"
        "eof '' Loc=<input.c:5:1>\n"
    )
    tokens, excluded, _ = parse_tokens(out, "input.c")
    assert excluded == 1
    assert tokens[1]["from_macro"] is True
    assert tokens[2]["text"] == '"%d"'
    assert len(tokens) == 3  # eof dropped


def test_tokens_malformed_output_counted():
    tokens, _, unparsed = parse_tokens("garbage line\nanother\n", "input.c")
    assert tokens == [] and unparsed == 2


# ------------------------------------------------------------- diagnostics
def test_diagnostics_from_real_output():
    src = (SAMPLES / "06_invalid.c").read_text()
    diags = parse_diagnostics(fixture_text("invalid.diag"), "input.c", src)
    errors = [d for d in diags if d["severity"] == "error"]
    assert len(errors) == 4
    assert errors[0]["category"] == "Parse Issue" and "expected ';'" in errors[0]["message"]
    assert errors[1]["category"] == "Semantic Issue" and "undeclared_var" in errors[1]["message"]
    assert errors[3]["flag"] == "-Wint-conversion"
    assert errors[1]["snippet"].strip().startswith("int y = undeclared_var")
    assert any(d["severity"] == "note" for d in diags)


def test_diagnostics_in_header_have_no_snippet():
    d = parse_diagnostics("C:\\inc\\x.h:3:1: warning: oops [-Wfoo]\n", "input.c", "int a;")
    assert d[0]["in_main_file"] is False and d[0]["snippet"] is None


# --------------------------------------------------------------------- AST
def test_ast_tree_main_file_only():
    data = json.loads(fixture_text("variables.ast.json"))
    tree = build_tree(data, "input.c")
    names = [n["name"] for n in tree["nodes"]]
    assert names == ["compute", "main"]
    compute = tree["nodes"][0]
    assert compute["kind"] == "FunctionDecl" and compute["line"] == 2
    assert tree["kind_counts"]["ParmVarDecl"] == 2
    assert tree["excluded"] > 0  # implicit builtin typedefs


def test_ast_location_tracking_carries_file_forward():
    ast = {"inner": [
        {"kind": "TypedefDecl", "name": "h", "loc": {"offset": 1, "file": "C:\\h.h", "line": 1, "col": 1}},
        {"kind": "TypedefDecl", "name": "h2", "loc": {"offset": 9, "line": 2, "col": 1}},  # still h.h
        {"kind": "FunctionDecl", "name": "f", "loc": {"offset": 0, "file": "input.c", "line": 1, "col": 5}},
        {"kind": "VarDecl", "name": "g", "loc": {"offset": 30, "line": 4, "col": 5}},       # still input.c
    ]}
    tree = build_tree(ast, "input.c")
    assert [n["name"] for n in tree["nodes"]] == ["f", "g"]
    assert tree["nodes"][1]["line"] == 4


# ---------------------------------------------------------------- LLVM IR
def test_ir_parse_counts_O0():
    mod = parse_module(fixture_text("constant_expr_O0.ll"))
    main = mod.functions["main"]
    c = main.opcode_counts
    assert c["alloca"] == 3 and c["add"] == 0  # 10 + 20 is folded by the frontend
    assert c["mul"] == 1 and c["sub"] == 1 and c["ret"] == 1
    assert mod.instruction_count == len(main.instructions)
    assert mod.target_triple


def test_ir_parse_O2_and_observations():
    base = parse_module(fixture_text("constant_expr_O0.ll"))
    opt = parse_module(fixture_text("constant_expr_O2.ll"))
    assert [i.text for i in opt.functions["main"].instructions] == ["ret i32 55"]
    obs = " ".join(observe(base, opt, "-O0", "-O2"))
    assert "ret i32 55" in obs and "constant folding" in obs
    assert "alloca" in obs


def test_ir_loops_blocks_and_phi():
    opt = parse_module(fixture_text("loops_O2.ll"))
    base = parse_module(fixture_text("loops_O0.ll"))
    assert base.functions["sum_to"].opcode_counts["br"] >= 3
    assert any(f.opcode_counts["phi"] for f in opt.defined)
    d = diff_function(base.functions["sum_to"], opt.functions["sum_to"])
    assert d["status"] == "changed"
    assert any(l["op"] == "removed" and "alloca" in l["text"] for l in d["lines"])


def test_opcode_extraction():
    assert opcode_of("%3 = add nsw i32 %1, %2") == "add"
    assert opcode_of("%r = tail call i32 @f(i32 1)") == "call"
    assert opcode_of("store i32 0, ptr %1, align 4") == "store"
    assert opcode_of("br label %5") == "br"


def test_normalize_ignores_names_and_metadata():
    assert normalize("%a = load i32, ptr %p, align 4, !tbaa !5") == normalize("%7 = load i32, ptr %2, align 4")


def test_identical_modules_reported_identical():
    m = parse_module(fixture_text("constant_expr_O2.ll"))
    assert "identical" in observe(m, m, "a", "b")[0]


def test_malformed_ir_does_not_crash():
    mod = parse_module("this is not IR\ndefine broken {\n  ???\n")
    assert mod.instruction_count == 0


# --------------------------------------------------------------- assembly
def test_assembly_filter_and_source_map():
    a = analyze_assembly(fixture_text("functions_O2.s"), "x86_64")
    lines = a["filtered"].splitlines()
    assert "sum_of_squares:" in lines and "main:" in lines
    assert not any(l.strip().startswith(".") for l in lines)  # no directives
    assert a["mnemonic_counts"].get("ret") == 2
    assert a["source_map"] and all(e["source_line"] > 0 for e in a["source_map"])


def test_assembly_counts_exclude_labels_directives_comments():
    asm = "\t.text\nf:\n\tpush\trbp # save\n.LBB0_1:\n\tjmp\t.LBB0_1\n# comment\n\t.p2align 4\n"
    a = analyze_assembly(asm, "x86_64")
    assert a["instruction_count"] == 2
    assert ".LBB0_1:" in a["filtered"]  # jump targets kept


def test_aarch64_immediates_not_treated_as_comments():
    a = analyze_assembly("f:\n\tmov\tw0, #25\n\tret\n", "aarch64")
    assert a["instruction_count"] == 2 and "#25" in a["filtered"]


# -------------------------------------------------------------------- PTX
def test_ptx_parse_real_output():
    mod = parse_ptx(fixture_text("cuda_kernel_O2.ptx"))
    names = [f.name for f in mod.functions]
    assert names == ["_Z5saxpyifPKfPf", "_Z9block_sumPKfPfi"]
    assert all(f.is_kernel for f in mod.functions)
    assert len(mod.functions[0].params) == 4
    s = summarize(mod)
    assert s["memory_ops"]["global"] >= 2
    assert s["memory_ops"]["shared"] >= 2       # block_sum uses __shared__
    assert s["class_counts"]["sync"] >= 1       # __syncthreads -> bar.sync
    assert s["branch_count"] >= 1
    assert mod.target == "sm_75"


def test_ptx_classification():
    assert classify("ld.global.f32") == "memory" and memory_space("ld.global.f32") == "global"
    assert memory_space("ld.f32") == "generic"
    assert classify("cvta.to.global.u64") == "conversion" and memory_space("cvta.to.global.u64") is None
    assert classify("bra.uni") == "control"
    assert classify("setp.ge.s32") == "compare/select"


def test_ptx_predicated_branch():
    ptx = ".visible .entry k(\n.param .u32 k_p\n)\n{\n.reg .pred %p<2>;\n@%p1 bra $L__BB0_2;\n$L__BB0_2:\nret;\n}\n"
    mod = parse_ptx(ptx)
    assert mod.functions[0].opcodes == ["bra", "ret"]
    assert mod.functions[0].reg_decls == [".reg .pred %p<2>"]
