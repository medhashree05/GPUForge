"""The single place where GPUForge launches external processes.

Rules enforced here:
* Arguments are always passed as a list (``shell=False``), so user input can
  never be interpreted by a shell.
* Every process has a timeout.
* Output is size-capped so a pathological program cannot exhaust memory.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import CompilerTimeoutError, ToolExecutionError


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _cap(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n... [output truncated by GPUForge]\n", True


def run_tool(
    command: list[str],
    cwd: Path | None = None,
    timeout_s: float | None = None,
    max_output_bytes: int | None = None,
) -> ProcessResult:
    settings = get_settings()
    timeout = timeout_s if timeout_s is not None else settings.compile_timeout_s
    if not command or not all(isinstance(a, str) for a in command):
        raise ToolExecutionError("Invalid command specification.")

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise CompilerTimeoutError(
            f"'{Path(command[0]).name}' did not finish within {timeout:g} s and was stopped."
        ) from exc
    except FileNotFoundError as exc:
        raise ToolExecutionError(f"Executable not found: {Path(command[0]).name}") from exc
    except OSError as exc:
        raise ToolExecutionError(f"Could not start {Path(command[0]).name}: {exc.strerror}") from exc
    duration_ms = (time.perf_counter() - start) * 1000

    limit = max_output_bytes or settings.max_output_bytes
    stdout, t1 = _cap(proc.stdout.decode("utf-8", errors="replace"), limit)
    stderr, t2 = _cap(proc.stderr.decode("utf-8", errors="replace"), limit)
    return ProcessResult(command, proc.returncode, stdout, stderr, duration_ms, t1 or t2)
