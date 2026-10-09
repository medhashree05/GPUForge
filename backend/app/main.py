"""GPUForge backend entry point: ``uvicorn app.main:app --reload`` (run from backend/)."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.errors import GPUForgeError

log = logging.getLogger("gpuforge")
settings = get_settings()

app = FastAPI(
    title="GPUForge API",
    description="Phase-by-phase analysis of real Clang/LLVM compiler output.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    # Source limit, plus room for JSON escaping and the other fields.
    limit = settings.max_source_bytes * 2 + 4096
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit:
        return JSONResponse(status_code=413, content={
            "error": {"code": "payload_too_large", "message": f"Request body exceeds {limit} bytes."}})
    return await call_next(request)


@app.exception_handler(GPUForgeError)
async def gpuforge_error(_: Request, exc: GPUForgeError):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={
        "error": {"code": "invalid_request", "message": "Request validation failed.", "details": details}})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)  # the trace stays in the server log only
    return JSONResponse(status_code=500, content={
        "error": {"code": "internal_error", "message": "An internal error occurred. See server logs."}})


app.include_router(api_router)
