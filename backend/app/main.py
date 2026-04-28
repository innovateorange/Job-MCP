"""
FastAPI App — Job-MCP
=====================
Entry point.  Mounts routers and exposes provider info.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import parse, apply
from backend.app.config import allowed_origin_regex

app = FastAPI(
    title="Job-MCP API",
    description="AI-powered job application pipeline — LangChain edition",
    version="2.0.0",
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
    import os
    from backend.app.services.llm_provider import LLMProvider

    return {
        "current_provider": os.getenv("LLM_PROVIDER", "custom"),
        "supported_providers": [p.value for p in LLMProvider],
        "note": (
            "Pass '?provider=<name>' or include 'provider' in the request body "
            "to override the default on any endpoint."
        ),
    }
