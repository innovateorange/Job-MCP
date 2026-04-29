"""
CORS configuration tests (#47).

The API must:
  - reflect the Origin header back ONLY for allowed origins,
  - NOT respond with CORS headers for disallowed origins,
  - restrict methods to a known list,
  - allow override via ALLOWED_ORIGIN_REGEX env var.

After review feedback (bug_001 / merged_bug_002): the default is now
localhost-only. Tests that previously relied on a default *.vercel.app
allowance now set the regex explicitly.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings


def _client_with_regex(monkeypatch, regex: str | None) -> TestClient:
    """Reload main with a specific ALLOWED_ORIGIN_REGEX env value."""
    if regex is None:
        monkeypatch.delenv("ALLOWED_ORIGIN_REGEX", raising=False)
    else:
        monkeypatch.setenv("ALLOWED_ORIGIN_REGEX", regex)

    # The middleware reads from Settings, so refresh the cached singleton
    # before reload re-evaluates the CORS config.
    get_settings.cache_clear()

    import backend.app.main as main_mod
    importlib.reload(main_mod)
    return TestClient(main_mod.app)


VERCEL_REGEX = (
    r"^http://localhost(:\d+)?$"
    r"|^https://[a-z0-9-]+\.vercel\.app$"
)


class TestDefaultOriginRegex:
    """Default regex is localhost-only — *.vercel.app is NOT trusted by default."""

    def test_localhost_allowed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_localhost_no_port_allowed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://localhost"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost"

    def test_arbitrary_vercel_subdomain_NOT_allowed_by_default(self, monkeypatch):
        """Default must not trust unrelated *.vercel.app projects."""
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "https://evilco.vercel.app"})
        assert r.status_code == 200
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}

    def test_arbitrary_origin_rejected(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "https://evil.example.com"})
        assert r.status_code == 200
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}

    def test_http_non_localhost_rejected(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://example.com"})
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}

    def test_empty_regex_falls_back_to_default(self, monkeypatch):
        """An empty ALLOWED_ORIGIN_REGEX must NOT deny everything."""
        client = _client_with_regex(monkeypatch, "")
        r = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestVercelOptIn:
    """When operators explicitly opt in to *.vercel.app, it works."""

    def test_vercel_subdomain_allowed_when_configured(self, monkeypatch):
        client = _client_with_regex(monkeypatch, VERCEL_REGEX)
        r = client.get("/", headers={"Origin": "https://job-mcp.vercel.app"})
        assert r.headers.get("access-control-allow-origin") == "https://job-mcp.vercel.app"


class TestPreflight:
    def test_preflight_allowed_origin_returns_methods(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert r.status_code == 200
        allow_methods = r.headers.get("access-control-allow-methods", "")
        for m in ("GET", "POST", "PATCH", "DELETE", "OPTIONS"):
            assert m in allow_methods

    def test_preflight_disallowed_origin_no_cors(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.options(
            "/",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


class TestEnvOverride:
    def test_custom_regex_allows_only_listed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, r"^https://prod\.example\.com$")

        ok = client.get("/", headers={"Origin": "https://prod.example.com"})
        assert ok.headers.get("access-control-allow-origin") == "https://prod.example.com"

        rejected = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" not in {k.lower() for k in rejected.headers}


@pytest.fixture(autouse=True)
def _restore_main(monkeypatch):
    """Reload main one final time after each test so other tests see the default."""
    yield
    monkeypatch.delenv("ALLOWED_ORIGIN_REGEX", raising=False)
    get_settings.cache_clear()
    import backend.app.main as main_mod
    importlib.reload(main_mod)
