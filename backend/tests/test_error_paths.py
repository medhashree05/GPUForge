"""Failure handling with mocked subprocesses / toolchains. None of these need
Clang or CUDA installed."""

import subprocess

import pytest

from app.core.toolchain_detection import ToolInfo
from app.services import ast_service, token_service
from app.utils import subprocess_runner
from app.utils.subprocess_runner import ProcessResult

SRC = {"source": "int main(void) { return 0; }", "language": "c"}
FAKE_CLANG = ToolInfo(name="clang", path="clang-fake", available=True, version="fake")


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_missing_clang_returns_503(client, fake_toolchain):
    fake_toolchain(clang=ToolInfo(name="clang", error="clang was not found"), ptx_method=None)
    r = client.post("/api/compile/ir", json=SRC)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "tool_unavailable"
    caps = client.get("/api/toolchain").json()["capabilities"]
    assert caps["ir"] is False and caps["ptx"] is False


def test_timeout_returns_504(client, fake_toolchain, monkeypatch):
    fake_toolchain(clang=FAKE_CLANG)

    def slow(*a, **kw):
        raise subprocess.TimeoutExpired(cmd=a[0], timeout=kw.get("timeout", 1))

    monkeypatch.setattr(subprocess_runner.subprocess, "run", slow)
    r = client.post("/api/compile/ir", json=SRC)
    assert r.status_code == 504
    assert "did not finish" in r.json()["error"]["message"]


def test_executable_vanished_returns_502(client, fake_toolchain, monkeypatch):
    fake_toolchain(clang=FAKE_CLANG)

    def missing(*a, **kw):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess_runner.subprocess, "run", missing)
    r = client.post("/api/compile/ir", json=SRC)
    assert r.status_code == 502
    assert "Traceback" not in r.text


def test_subprocess_uses_argument_list_without_shell(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(subprocess_runner.subprocess, "run", fake_run)
    subprocess_runner.run_tool(["clang", "a; rm -rf /"])
    assert seen["shell"] is False and isinstance(seen["cmd"], list)
    assert seen["timeout"] > 0


def test_output_is_capped(monkeypatch):
    monkeypatch.setattr(subprocess_runner.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, b"x" * 5000, b""))
    res = subprocess_runner.run_tool(["tool"], max_output_bytes=100)
    assert res.truncated and len(res.stdout) < 200


def _fake_clang_output(monkeypatch, module, stdout="", stderr="", code=0):
    monkeypatch.setattr(module, "run_clang",
                        lambda ctx, args, **kw: ProcessResult(["clang", *args], code, stdout, stderr, 1.0))


def test_malformed_ast_output_is_reported_not_crashed(client, fake_toolchain, monkeypatch):
    fake_toolchain(clang=FAKE_CLANG)
    _fake_clang_output(monkeypatch, ast_service, stdout="{not json", code=0)
    r = client.post("/api/analyze/ast", json=SRC)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert any("could not be parsed" in w for w in body["warnings"])


def test_malformed_token_output(client, fake_toolchain, monkeypatch):
    fake_toolchain(clang=FAKE_CLANG)
    _fake_clang_output(monkeypatch, token_service, stderr="??? unexpected format\n")
    body = client.post("/api/analyze/tokens", json=SRC).json()
    assert body["status"] == "failed" and body["token_count"] == 0
    assert any("could not be parsed" in w for w in body["warnings"])


def test_ptx_unavailable_is_unsupported_not_fabricated(client, fake_toolchain):
    fake_toolchain(ptx_method=None)
    r = client.post("/api/compile/ptx", json={"source": "__global__ void k(){}", "language": "cuda"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unsupported"
    assert body["ptx"] == "" and body["summary"] is None
    assert "No PTX toolchain" in body["message"]


def test_ptx_requires_cuda_language(client):
    body = client.post("/api/compile/ptx", json=SRC).json()
    assert body["status"] == "unsupported"


def test_unhandled_error_hides_trace(client, fake_toolchain, monkeypatch):
    fake_toolchain(clang=FAKE_CLANG)

    def boom(ctx):
        raise RuntimeError("secret internal detail")

    from app.api import compilation
    monkeypatch.setattr(compilation, "generate_ir", boom)
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app, raise_server_exceptions=False).post("/api/compile/ir", json=SRC)
    assert r.status_code == 500
    assert "secret internal detail" not in r.text


@pytest.mark.parametrize("missing_opt", [True])
def test_missing_opt_disables_pass_features(client, fake_toolchain, missing_opt):
    fake_toolchain(opt=ToolInfo(name="opt", error="not found"))
    tc = client.get("/api/toolchain").json()
    assert tc["capabilities"]["individual_passes"] is False
    assert tc["allowed_passes"] == {}
