"""End-to-end tests running the real installed Clang/LLVM. Skipped when Clang is
absent. Assertions check properties of the *actual* compiler output."""

import pytest

from tests.conftest import requires_clang

pytestmark = requires_clang


def post(client, path, **body):
    r = client.post(path, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_toolchain_reports_real_clang(client):
    tc = client.get("/api/toolchain").json()
    assert tc["clang"]["available"] and "clang version" in tc["clang"]["version"]
    assert tc["host_triple"] and tc["host_arch"]


def test_samples_endpoint(client):
    ids = {s["id"] for s in client.get("/api/samples").json()}
    assert {"constant_expr", "invalid", "redundant", "cuda_kernel"} <= ids


@pytest.mark.parametrize("sid", ["constant_expr", "variables", "functions", "conditionals", "loops", "redundant"])
def test_valid_c_programs_full_pipeline(client, samples, sid):
    s = samples[sid]
    d = post(client, "/api/analyze/full", source=s["source"], language=s["language"])
    for phase in ("tokens", "ast", "diagnostics", "ir", "optimization", "assembly"):
        assert d[phase]["status"] == "success", (phase, d[phase]["message"])
    assert d["ptx"]["status"] == "unsupported"
    assert "define" in d["ir"]["ir"] and d["ir"]["instruction_count"] > 0
    assert d["assembly"]["instruction_count"] > 0
    assert d["optimization"]["optimized_count"] <= d["optimization"]["baseline_count"]


def test_valid_cpp_program(client, samples):
    s = samples["cpp_class"]
    d = post(client, "/api/analyze/full", source=s["source"], language="cpp")
    assert d["diagnostics"]["semantic_ok"]
    assert d["ast"]["status"] == "success"
    kinds = d["ast"]["kind_counts"]
    assert "CXXRecordDecl" in kinds and "FunctionTemplateDecl" in kinds


def test_tokenization_of_valid_tokens_but_invalid_program(client):
    # Every token is lexically valid, but the program is not.
    src = "int main(void) { return x + ; }"
    toks = post(client, "/api/analyze/tokens", source=src)
    assert toks["token_count"] > 0
    diags = post(client, "/api/analyze/diagnostics", source=src)
    assert diags["status"] == "failed" and not diags["semantic_ok"]


@pytest.mark.parametrize("src, needle, category", [
    ("int main(void){ return y; }", "undeclared identifier", "Semantic Issue"),
    ("int main(void){ int a = 1 return a; }", "expected ';'", "Parse Issue"),
    ("int f(int a, int b){return a+b;}\nint main(void){ return f(1); }", "too few arguments", "Semantic Issue"),
    ("struct S{int a;};\nint main(void){ struct S s; return s + 1; }", "invalid operands", "Semantic Issue"),
    ("void f(void){ return 1; }\nint main(void){ f(); return 0; }", "should not return a value", "Semantic Issue"),
])
def test_semantic_and_syntax_errors(client, src, needle, category):
    d = post(client, "/api/analyze/diagnostics", source=src)
    assert d["status"] == "failed" and d["error_count"] >= 1
    err = next(x for x in d["diagnostics"] if x["severity"] == "error")
    assert needle in err["message"]
    assert err["category"] == category
    assert err["line"] is not None and err["snippet"]


def test_invalid_program_skips_codegen(client, samples):
    s = samples["invalid"]
    d = post(client, "/api/analyze/full", source=s["source"], language="c")
    assert d["diagnostics"]["error_count"] == 4
    assert d["ir"]["status"] == "skipped" and d["assembly"]["status"] == "skipped"
    assert d["ast"]["node_count"] > 0  # Clang still recovers a partial AST


def test_ir_endpoint_respects_opt_level(client, samples):
    src = samples["constant_expr"]["source"]
    o0 = post(client, "/api/compile/ir", source=src, opt_level="O0")
    o2 = post(client, "/api/compile/ir", source=src, opt_level="O2")
    assert o0["opcode_counts"].get("alloca", 0) > 0
    assert "alloca" not in o2["opcode_counts"]
    assert o2["instruction_count"] < o0["instruction_count"]
    assert {e["opcode"] for e in o0["explanations"]} <= set(o0["opcode_counts"])


def test_constant_folding_observed_from_real_output(client, samples):
    d = post(client, "/api/analyze/optimization", source=samples["constant_expr"]["source"])
    main = next(f for f in d["function_diffs"] if f["name"] == "main")
    optimized = [l["text"].strip() for l in main["lines"] if l["op"] != "removed" and not l["text"].endswith(":")]
    assert optimized == ["ret i32 55"]  # (10 + 20) * 2 - 5, computed by the compiler
    assert any("compile time" in o for o in d["observations"])
    assert d["pass_timeline"], d["pass_timeline_note"]
    assert "verified to match" in d["pass_timeline_note"]


def test_dead_branch_removed(client, samples):
    d = post(client, "/api/analyze/optimization", source=samples["conditionals"]["source"])
    main = next(f for f in d["function_diffs"] if f["name"] == "main")
    assert main["optimized_count"] < main["baseline_count"]
    assert "br" not in [l["text"].split()[0] for l in main["lines"] if l["op"] == "added"]


def test_individual_pass_mem2reg(client, samples):
    d = post(client, "/api/analyze/optimization", source=samples["variables"]["source"], passes=["mem2reg"])
    assert d["mode"] == "passes"
    assert d["opcode_delta"]["alloca"][0] > 0 and d["opcode_delta"]["alloca"][1] == 0
    assert any(p["pass_name"].startswith("PromotePass") for p in d["pass_timeline"])


def test_pass_that_changes_nothing(client):
    d = post(client, "/api/analyze/optimization", source="int main(void){return 0;}", passes=["licm"])
    assert d["pass_timeline"] == []
    assert "did not change" in d["observations"][0]


def test_assembly_labels_target_and_compares_levels(client, samples, real_toolchain):
    d = post(client, "/api/compile/assembly", source=samples["functions"]["source"], opt_level="O2")
    assert d["arch"] == real_toolchain.host_arch
    assert d["target_triple"] == real_toolchain.host_triple
    levels = {v["opt_level"]: v["instruction_count"] for v in d["comparison"]}
    assert levels["O2"] < levels["O0"]
    assert d["source_map"]
    assert "gpuforge_" not in d["asm"]  # no server temp paths leak


@pytest.mark.skipif("not __import__('app.core.toolchain_detection', fromlist=['x']).get_toolchain().ptx_method")
def test_ptx_generation_when_available(client, samples):
    s = samples["cuda_kernel"]
    d = post(client, "/api/compile/ptx", source=s["source"], language="cuda", opt_level="O2",
             compare_opt_level="O0")
    assert d["status"] == "success"
    assert ".entry" in d["ptx"] and d["ptx_version"]
    assert {f["name"] for f in d["functions"] if f["is_kernel"]} == {"_Z5saxpyifPKfPf", "_Z9block_sumPKfPfi"}
    assert d["summary"]["memory_ops"].get("shared", 0) > 0
    assert d["comparison"]["opt_level"] == "O0"
    assert any("not execution speed" in w for w in d["warnings"])


def test_metrics_mark_unavailable_values(client, samples):
    m = post(client, "/api/analyze/metrics", source=samples["invalid"]["source"])
    by_key = {x["key"]: x for x in m["metrics"]}
    assert by_key["ir_instructions"]["value"] is None
    assert by_key["errors"]["value"] == 4
    assert all(x["definition"] for x in m["metrics"])
