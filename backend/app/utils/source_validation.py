"""Validation of untrusted source code before it reaches the compiler.

Clang will happily ``#include`` any file it can read and echo its contents back
in diagnostics or token dumps. Because GPUForge returns compiler output to the
browser, we block include/embed forms that could read arbitrary files.
This is a best-effort filter for a local tool, not a sandbox (see README).
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.errors import SourceValidationError

# `#  include`, `#include_next`, `#import`, `#embed`, with optional spaces after '#'.
_DIRECTIVE = re.compile(r"^\s*#\s*(include_next|include|import|embed)\b\s*(.*)$", re.MULTILINE)
_HAS_INCLUDE = re.compile(r"__has_(include|include_next|embed)\s*\(\s*\"")
_ALLOWED_HEADER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./+-]*$")


def validate_source(source: str) -> None:
    settings = get_settings()
    if not source or not source.strip():
        raise SourceValidationError("Source code is empty.")
    size = len(source.encode("utf-8"))
    if size > settings.max_source_bytes:
        raise SourceValidationError(
            f"Source is {size} bytes; the limit is {settings.max_source_bytes} bytes."
        )
    if "\x00" in source:
        raise SourceValidationError("Source contains NUL bytes.")
    if "??=" in source:
        # Trigraph '#' could hide a directive from the checks below.
        raise SourceValidationError("Trigraphs ('??=') are not supported.")
    # Check the text after removing backslash line-splices, as the preprocessor sees it.
    spliced = source.replace("\\\r\n", "").replace("\\\n", "")
    for m in _DIRECTIVE.finditer(spliced):
        _check_directive(m.group(1), m.group(2))
    if _HAS_INCLUDE.search(spliced):
        raise SourceValidationError("Quoted __has_include/__has_embed checks are not allowed.")


def _check_directive(kind: str, rest: str) -> None:
    rest = rest.strip()
    if kind == "embed":
        raise SourceValidationError("#embed is disabled (it can read arbitrary files).")
    if rest.startswith("<") and ">" in rest:
        header = rest[1 : rest.index(">")].strip()
    elif rest.startswith('"'):
        raise SourceValidationError(
            'Quoted includes (#include "file") are disabled; only <system> headers are allowed.'
        )
    else:
        raise SourceValidationError("Computed (macro-based) includes are not allowed.")
    if not _ALLOWED_HEADER.match(header) or ".." in header or ":" in header:
        raise SourceValidationError(f"Header name '<{header}>' is not allowed.")
