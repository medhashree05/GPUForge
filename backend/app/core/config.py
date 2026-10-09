"""Application configuration.

All settings can be overridden with environment variables prefixed with
``GPUFORGE_`` or through a ``backend/.env`` file (see ``.env.example``).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GPUFORGE_", env_file=BACKEND_DIR / ".env", extra="ignore"
    )

    # Directory containing clang, opt, llc ... (optional; PATH is searched too).
    llvm_bin_dir: str | None = None
    # Explicit executable paths (optional; override discovery).
    clang_path: str | None = None
    opt_path: str | None = None
    nvcc_path: str | None = None

    # Process limits.
    compile_timeout_s: float = 20.0
    max_source_bytes: int = 64 * 1024
    max_output_bytes: int = 8 * 1024 * 1024

    # Where per-request temporary directories are created (None = OS temp).
    work_root: str | None = None

    samples_dir: Path = PROJECT_DIR / "samples"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
