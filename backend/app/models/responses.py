"""Response schemas. Every phase response carries ``status`` and the exact
commands that produced it, so the UI can show *how* each output was obtained."""

from typing import Literal

from pydantic import BaseModel, Field

# skipped = not attempted because an earlier phase failed (e.g. compile errors)
PhaseStatus = Literal["success", "failed", "unsupported", "skipped"]


class CommandInfo(BaseModel):
    command: list[str]
    exit_code: int
    duration_ms: float


class PhaseResponse(BaseModel):
    phase: str
    status: PhaseStatus
    message: str = ""
    commands: list[CommandInfo] = Field(default_factory=list)
    compiler_stderr: str = ""
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- toolchain
class ToolStatus(BaseModel):
    name: str
    available: bool
    path: str | None
    version: str | None
    error: str | None


class ToolchainResponse(BaseModel):
    clang: ToolStatus
    opt: ToolStatus
    nvcc: ToolStatus
    host_triple: str | None
    host_arch: str | None
    nvptx_backend: bool
    system_headers: bool
    system_headers_error: str | None
    ptx_method: str | None
    capabilities: dict[str, bool]
    notes: list[str]
    allowed_passes: dict[str, str]
    allowed_gpu_archs: list[str]


# ------------------------------------------------------------------- tokens
class Token(BaseModel):
    kind: str
    text: str
    line: int | None
    column: int | None
    flags: list[str] = Field(default_factory=list)
    from_macro: bool = False


class TokensResponse(PhaseResponse):
    tokens: list[Token] = Field(default_factory=list)
    token_count: int = 0
    kind_counts: dict[str, int] = Field(default_factory=dict)
    header_tokens_excluded: int = 0


# ---------------------------------------------------------------------- AST
class ASTNode(BaseModel):
    id: str
    kind: str
    name: str | None = None
    type: str | None = None
    detail: str | None = None
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    implicit: bool = False
    children: list["ASTNode"] = Field(default_factory=list)


class ASTResponse(PhaseResponse):
    nodes: list[ASTNode] = Field(default_factory=list)
    node_count: int = 0
    kind_counts: dict[str, int] = Field(default_factory=dict)
    raw_text: str = ""
    header_decls_excluded: int = 0


# -------------------------------------------------------------- diagnostics
class Diagnostic(BaseModel):
    severity: Literal["error", "warning", "note", "remark", "fatal error"]
    message: str
    line: int | None
    column: int | None
    category: str | None = None
    flag: str | None = None
    in_main_file: bool = True
    snippet: str | None = None


class DiagnosticsResponse(PhaseResponse):
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    # Did -fsyntax-only (parse + semantic analysis) finish without errors?
    semantic_ok: bool = False


# ----------------------------------------------------------------------- IR
class InstructionExplanation(BaseModel):
    opcode: str
    count: int
    explanation: str


class IRFunction(BaseModel):
    name: str
    instruction_count: int
    block_count: int
    is_declaration: bool = False


class IRResponse(PhaseResponse):
    ir: str = ""
    opt_level: str = ""
    target_triple: str | None = None
    instruction_count: int = 0
    opcode_counts: dict[str, int] = Field(default_factory=dict)
    functions: list[IRFunction] = Field(default_factory=list)
    explanations: list[InstructionExplanation] = Field(default_factory=list)


# ------------------------------------------------------------- optimization
class DiffLine(BaseModel):
    op: Literal["equal", "added", "removed"]
    text: str


class FunctionDiff(BaseModel):
    name: str
    status: Literal["changed", "unchanged", "removed", "added"]
    baseline_count: int
    optimized_count: int
    lines: list[DiffLine]


class PassChange(BaseModel):
    pass_name: str
    scope: str


class OptimizationResponse(PhaseResponse):
    mode: Literal["levels", "passes"] = "levels"
    baseline_label: str = ""
    optimized_label: str = ""
    baseline_ir: str = ""
    optimized_ir: str = ""
    baseline_count: int = 0
    optimized_count: int = 0
    opcode_delta: dict[str, list[int]] = Field(default_factory=dict)
    function_diffs: list[FunctionDiff] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    pass_timeline: list[PassChange] = Field(default_factory=list)
    pass_timeline_note: str = ""


# ----------------------------------------------------------------- assembly
class SourceMapEntry(BaseModel):
    asm_line: int  # 1-based line in `filtered_asm`
    source_line: int


class AsmVariant(BaseModel):
    opt_level: str
    instruction_count: int
    mnemonic_counts: dict[str, int]


class AssemblyResponse(PhaseResponse):
    asm: str = ""
    filtered_asm: str = ""
    target_triple: str | None = None
    arch: str | None = None
    opt_level: str = ""
    instruction_count: int = 0
    mnemonic_counts: dict[str, int] = Field(default_factory=dict)
    counting_method: str = ""
    source_map: list[SourceMapEntry] = Field(default_factory=list)
    comparison: list[AsmVariant] = Field(default_factory=list)
    explanations: list[InstructionExplanation] = Field(default_factory=list)


# ---------------------------------------------------------------------- PTX
class PTXFunction(BaseModel):
    name: str
    is_kernel: bool
    instruction_count: int
    params: list[str]


class PTXSummary(BaseModel):
    opt_level: str
    instruction_count: int
    class_counts: dict[str, int]
    opcode_counts: dict[str, int]
    memory_ops: dict[str, int]
    branch_count: int


class PTXResponse(PhaseResponse):
    ptx: str = ""
    method: str | None = None
    gpu_arch: str = ""
    ptx_version: str | None = None
    target: str | None = None
    functions: list[PTXFunction] = Field(default_factory=list)
    register_decls: list[str] = Field(default_factory=list)
    summary: PTXSummary | None = None
    comparison: PTXSummary | None = None
    explanations: list[InstructionExplanation] = Field(default_factory=list)


# ------------------------------------------------------------------ metrics
class Metric(BaseModel):
    key: str
    label: str
    value: float | int | str | None  # None => "Unavailable"
    unit: str = ""
    definition: str
    limitation: str = ""


class MetricsResponse(PhaseResponse):
    metrics: list[Metric] = Field(default_factory=list)


class FullAnalysisResponse(BaseModel):
    tokens: TokensResponse
    ast: ASTResponse
    diagnostics: DiagnosticsResponse
    ir: IRResponse
    optimization: OptimizationResponse
    assembly: AssemblyResponse
    ptx: PTXResponse
    metrics: MetricsResponse


class Sample(BaseModel):
    id: str
    title: str
    language: str
    description: str
    source: str
