"""
Runtime configuration for the Job-MCP backend.

Issue #47: lock down CORS to known origins via allow_origin_regex.
"""

from __future__ import annotations

import os

# Default allowed origins: localhost (any port) + any *.vercel.app subdomain.
# Production deployments should override ALLOWED_ORIGIN_REGEX with the exact
# project URLs to avoid trusting unrelated Vercel deployments.
DEFAULT_ALLOWED_ORIGIN_REGEX = (
    r"^http://localhost(:\d+)?$"
    r"|^https://[a-z0-9-]+\.vercel\.app$"
)


def allowed_origin_regex() -> str:
    return os.getenv("ALLOWED_ORIGIN_REGEX", DEFAULT_ALLOWED_ORIGIN_REGEX)

