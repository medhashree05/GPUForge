"""Request validation and source-security checks (no compiler needed:
validation runs before any tool is invoked)."""

import pytest

from app.core.errors import SourceValidationError
from app.utils.source_validation import validate_source


@pytest.mark.parametrize("source", [
    '#include "secret.txt"\nint main(void){return 0;}',
    "#include <../../etc/passwd>\n",
    "#include <C:/Windows/win.ini>\n",
    "#define F <stdio.h>\n#include F\n",
    "#embed </etc/passwd>\n",
    '#if __has_include("x.h")\n#endif\n',
    "#  include_next <stdio.h>\n#include \"a\"\n",
    "#incl\\\nude \"x.txt\"\n",            # line splice hiding a directive
    "??=include \"x\"\n",                   # trigraph
])
def test_dangerous_includes_rejected(source):
    with pytest.raises(SourceValidationError):
        validate_source(source)


@pytest.mark.parametrize("source", [
    "#include <stdio.h>\nint main(void){return 0;}",
    "#include <sys/types.h>\n",
    "  #  include <cstdio>\n",
    "int main(void) { return 0; }",
])
def test_safe_sources_accepted(source):
    validate_source(source)


def test_empty_source_rejected(client):
    r = client.post("/api/compile/ir", json={"source": "   \n", "language": "c"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_source"


def test_oversized_source_rejected(client):
    from app.core.config import get_settings
    big = "int x;\n" * (get_settings().max_source_bytes // 7 + 10)
    r = client.post("/api/compile/ir", json={"source": big, "language": "c"})
    assert r.status_code in (413, 422)
    assert "error" in r.json()


def test_huge_body_rejected_before_parsing(client):
    r = client.post("/api/compile/ir", content=b"x" * 500_000, headers={"content-type": "application/json"})
    assert r.status_code == 413


@pytest.mark.parametrize("payload, field", [
    ({"source": "int x;", "language": "rust"}, "language"),
    ({"source": "int x;", "opt_level": "O9"}, "opt_level"),
    ({"source": "int x;", "gpu_arch": "sm_1000"}, "gpu_arch"),
    ({"language": "c"}, "source"),
])
def test_invalid_payloads(client, payload, field):
    r = client.post("/api/compile/ir", json=payload)
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "invalid_request"
    assert any(d["field"] == field for d in body["details"])


def test_disallowed_pass_rejected(client):
    r = client.post("/api/analyze/optimization",
                    json={"source": "int main(void){return 0;}", "passes": ["load=evil.dll"]})
    assert r.status_code == 422


def test_quoted_include_rejected_via_api(client):
    r = client.post("/api/analyze/tokens", json={"source": '#include "x.h"\n', "language": "c"})
    assert r.status_code == 422
    assert "Quoted includes" in r.json()["error"]["message"]
