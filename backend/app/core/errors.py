"""Domain errors. Each maps to a safe, user-facing HTTP error (no stack traces)."""


class GPUForgeError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SourceValidationError(GPUForgeError):
    status_code = 422
    code = "invalid_source"


class ToolNotAvailableError(GPUForgeError):
    status_code = 503
    code = "tool_unavailable"


class CompilerTimeoutError(GPUForgeError):
    status_code = 504
    code = "compiler_timeout"


class ToolExecutionError(GPUForgeError):
    """The tool could not be started or produced unusable output."""

    status_code = 502
    code = "tool_execution_failed"
