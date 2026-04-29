"""
FastAPI App — Job-MCP
=====================
Entry point.  Mounts routers and exposes provider info.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import Settings, allowed_origin_regex, get_settings
from backend.app.routers import apply, parse

logger = logging.getLogger(__name__)


async def _probe_supabase(settings: Settings) -> None:
    url, key = settings.supabase_credentials()
    if not url or not key:
        missing = [
            name
            for name, v in (
                ("SUPABASE_URL", url),
                ("SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY", key),
            )
            if not v
        ]
        logger.info("supabase probe skipped (missing %s)", ", ".join(missing))
        return
    from supabase import create_client

    client = create_client(url, key)
    client.table("job_applications").select("id").limit(1).execute()


async def _probe_redis(settings: Settings) -> None:
    import redis

    # Both timeouts matter: socket_connect_timeout bounds the TCP handshake,
    # socket_timeout bounds the PING round-trip. Without the latter, a Redis
    # that accepts connections but is unresponsive (e.g. mid-BGSAVE) will
    # hang the lifespan startup forever.
    r = redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        r.ping()
    finally:
        try:
            r.close()
        except Exception:
            pass


async def _probe_llm_provider(settings: Settings) -> None:
    """Construct (don't call) the configured provider to surface config errors."""
    from backend.app.services.llm_provider import get_llm

    get_llm(provider=settings.llm_provider)


async def run_startup_probe(settings: Settings) -> None:
    """Fail fast if required services are misconfigured. Idempotent."""
    failures: list[str] = []
    for name, probe in (
        ("supabase", _probe_supabase),
        ("redis", _probe_redis),
        ("llm_provider", _probe_llm_provider),
    ):
        try:
            await probe(settings)
            logger.info("startup probe ok: %s", name)
        except Exception as exc:
            failures.append(f"{name}: {exc!r}")
            logger.exception("startup probe failed: %s", name)
    if failures:
        raise RuntimeError("startup probe failed:\n  - " + "\n  - ".join(failures))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.startup_probe_skip:
        logger.info("startup probe skipped via STARTUP_PROBE_SKIP=1")
    else:
        await run_startup_probe(settings)
    yield


app = FastAPI(
    title="Job-MCP API",
    description="AI-powered job application pipeline — LangChain edition",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=allowed_origin_regex(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    max_age=600,
)

app.include_router(parse.router)
app.include_router(apply.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Job-MCP API v2 — LangChain edition"}


@app.get("/providers")
async def list_providers():
    """List all supported LLM providers and the currently configured default."""
    from backend.app.services.llm_provider import LLMProvider

    return {
        "current_provider": get_settings().llm_provider,
        "supported_providers": [p.value for p in LLMProvider],
        "note": (
            "Pass '?provider=<name>' or include 'provider' in the request body "
            "to override the default on any endpoint."
        ),
    }
