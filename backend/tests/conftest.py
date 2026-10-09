import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import toolchain_detection
from app.core.toolchain_detection import Toolchain, ToolInfo, get_toolchain
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLES = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def real_toolchain() -> Toolchain:
    return get_toolchain()


@pytest.fixture(scope="session")
def samples() -> dict[str, dict]:
    manifest = json.loads((SAMPLES / "samples.json").read_text())
    return {s["id"]: {**s, "source": (SAMPLES / s["file"]).read_text()} for s in manifest}


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def clang_available() -> bool:
    return get_toolchain().clang.available


requires_clang = pytest.mark.skipif(not clang_available(), reason="Clang is not installed")


@pytest.fixture
def fake_toolchain():
    """Temporarily replace the detected toolchain; restores the real one afterwards."""
    original = get_toolchain()

    def install(**overrides) -> Toolchain:
        tc = Toolchain(
            clang=overrides.pop("clang", original.clang),
            opt=overrides.pop("opt", original.opt),
            nvcc=overrides.pop("nvcc", ToolInfo(name="nvcc")),
            host_triple=original.host_triple, host_arch=original.host_arch,
            nvptx_backend=original.nvptx_backend, system_headers=original.system_headers,
            ptx_method=original.ptx_method, opt_passes=original.opt_passes,
        )
        for k, v in overrides.items():
            setattr(tc, k, v)
        toolchain_detection.set_toolchain_for_tests(tc)
        return tc

    yield install
    toolchain_detection.set_toolchain_for_tests(original)
