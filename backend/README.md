# GPUForge backend

FastAPI service that runs Clang/LLVM on submitted source and returns structured, phase-by-phase
results. See the [root README](../README.md) for setup, API reference and the security model, and
[docs/MODULE_NOTES.md](../docs/MODULE_NOTES.md) for per-module notes.

```bash
python -m venv .venv && .venv\Scripts\activate      # Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                # set GPUFORGE_LLVM_BIN_DIR if clang is not on PATH
python -m uvicorn app.main:app --port 8000          # API docs: http://127.0.0.1:8000/docs
python -m pytest -q                                 # tests (integration tests skip without clang)
python -m tests.fixtures.regenerate                 # re-capture parser fixtures from real clang
```

Layout: `app/api` (routes) → `app/services` (one per phase) → `app/parsers` (pure text parsers) and
`app/utils/subprocess_runner.py` (the only place processes are started).
