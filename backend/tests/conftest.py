"""Shared pytest configuration for backend tests."""

from __future__ import annotations

import os

# Skip the FastAPI lifespan startup probe in tests — we don't want to
# require a live Supabase/Redis to run unit tests.
os.environ.setdefault("STARTUP_PROBE_SKIP", "1")
