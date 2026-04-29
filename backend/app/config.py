"""
Runtime configuration for the Job-MCP backend.

Issue #47: lock down CORS to known origins via allow_origin_regex.
Issue #48: validate environment variables at startup with Pydantic Settings.

`get_settings()` is cached and authoritative; prefer it over `os.getenv()`
in new code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor the env file to the module location so it resolves regardless of
# the process CWD (uvicorn from the repo root vs. Docker WORKDIR=/app, etc.).
# `Path(__file__).resolve().parent.parent` -> backend/.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Conservative default: localhost only. Production deployments MUST set
# ALLOWED_ORIGIN_REGEX explicitly to their own URLs. This is intentionally
# stricter than `*.vercel.app` because that pattern would let any free
# Vercel subdomain make credentialed cross-origin requests.
DEFAULT_ALLOWED_ORIGIN_REGEX = r"^http://localhost(:\d+)?$"


class Settings(BaseSettings):
    """Authoritative app configuration, validated at construction time."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Supabase ───────────────────────────────────────────────────────
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_key: str | None = None  # legacy fallback name

    # ── Redis (Celery broker / cache) ──────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── CORS ───────────────────────────────────────────────────────────
    allowed_origin_regex: str = DEFAULT_ALLOWED_ORIGIN_REGEX

    # ── LLM core ───────────────────────────────────────────────────────
    llm_provider: str = "custom"
    llm_model: str = "fine-tuned-job-mcp"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # ── Provider credentials (each optional; validated by llm_provider) ─
    custom_llm_base_url: str = "http://localhost:8080/v1"
    custom_llm_api_key: str = "not-needed"

    anthropic_api_key: str | None = None

    openai_api_key: str | None = None

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str | None = None

    huggingface_api_token: str | None = None
    huggingface_endpoint_url: str | None = None

    ollama_base_url: str | None = None

    # ── Ops ────────────────────────────────────────────────────────────
    startup_probe_skip: bool = False

    @model_validator(mode="after")
    def _check_provider_credentials(self) -> "Settings":
        """If LLM_PROVIDER picks a hosted backend, its keys must be present."""
        provider = self.llm_provider.lower()
        required: dict[str, tuple[str, ...]] = {
            "anthropic": ("anthropic_api_key",),
            "openai": ("openai_api_key",),
            "azure_openai": (
                "azure_openai_endpoint",
                "azure_openai_api_key",
                "azure_openai_deployment",
            ),
            "huggingface": ("huggingface_api_token",),
        }
        missing = [k for k in required.get(provider, ()) if not getattr(self, k)]
        if missing:
            keys_upper = ", ".join(k.upper() for k in missing)
            raise ValueError(
                f"LLM_PROVIDER={provider!r} requires {keys_upper}. "
                "Set the missing variable(s) or change LLM_PROVIDER."
            )
        return self

    def supabase_credentials(self) -> tuple[str | None, str | None]:
        """Return (url, key) preferring service-role key over the legacy key var."""
        return self.supabase_url, self.supabase_service_role_key or self.supabase_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton. Call ``get_settings.cache_clear()`` to reload."""
    return Settings()


def allowed_origin_regex() -> str:
    """Origin regex used by the CORS middleware.

    Reads from ``Settings`` (which loads ``backend/.env`` via pydantic-settings)
    so that values placed in the dotenv file are actually honored. An empty
    string falls back to the safe default rather than denying everything.
    """
    value = get_settings().allowed_origin_regex
    return value or DEFAULT_ALLOWED_ORIGIN_REGEX
