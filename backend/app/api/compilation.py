"""Phase endpoints. Each request: validate → private temp dir → run Clang → parse."""

from typing import Callable, TypeVar

from fastapi import APIRouter

from app.core.security import request_workdir
from app.models.requests import AssemblyRequest, OptimizationRequest, PTXRequest, SourceRequest
from app.models.responses import (
    ASTResponse, AssemblyResponse, DiagnosticsResponse, FullAnalysisResponse, IRResponse,
    MetricsResponse, OptimizationResponse, PTXResponse, TokensResponse,
)
from app.services.analysis_service import run_full
from app.services.assembly_service import generate_assembly
from app.services.ast_service import analyze_ast
from app.services.compiler_service import CompileContext, prepare
from app.services.diagnostics_service import analyze_diagnostics
from app.services.ir_service import generate_ir
from app.services.optimization_service import analyze_optimization
from app.services.ptx_service import generate_ptx
from app.services.token_service import analyze_tokens

router = APIRouter(tags=["compilation"])
T = TypeVar("T")


def _run(req: SourceRequest, fn: Callable[[CompileContext], T]) -> T:
    with request_workdir() as wd:
        return fn(prepare(req, wd))


@router.post("/analyze/tokens", response_model=TokensResponse)
def tokens(req: SourceRequest):
    return _run(req, analyze_tokens)


@router.post("/analyze/ast", response_model=ASTResponse)
def ast(req: SourceRequest):
    return _run(req, analyze_ast)


@router.post("/analyze/diagnostics", response_model=DiagnosticsResponse)
def diagnostics(req: SourceRequest):
    return _run(req, analyze_diagnostics)


@router.post("/compile/ir", response_model=IRResponse)
def ir(req: SourceRequest):
    return _run(req, generate_ir)


@router.post("/analyze/optimization", response_model=OptimizationResponse)
def optimization(req: OptimizationRequest):
    return _run(req, analyze_optimization)


@router.post("/compile/assembly", response_model=AssemblyResponse)
def assembly(req: AssemblyRequest):
    return _run(req, generate_assembly)


@router.post("/compile/ptx", response_model=PTXResponse)
def ptx(req: PTXRequest):
    return _run(req, generate_ptx)


@router.post("/analyze/metrics", response_model=MetricsResponse)
def metrics(req: SourceRequest):
    return _run(req, lambda ctx: run_full(ctx).metrics)


@router.post("/analyze/full", response_model=FullAnalysisResponse)
def full(req: SourceRequest):
    """Run every phase in one request (what the UI's "Compile & Analyze" uses)."""
    return _run(req, run_full)
