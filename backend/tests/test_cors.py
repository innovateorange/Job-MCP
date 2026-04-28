"""
CORS configuration tests (#47).

The API must:
  - reflect the Origin header back ONLY for allowed origins,
  - NOT respond with CORS headers for disallowed origins,
  - restrict methods to a known list,
  - allow override via ALLOWED_ORIGIN_REGEX env var.
"""

import importlib

import pytest
from fastapi.testclient import TestClient


def _client_with_regex(monkeypatch, regex: str | None) -> TestClient:
    """Reload main with a specific ALLOWED_ORIGIN_REGEX env value."""
    if regex is None:
        monkeypatch.delenv("ALLOWED_ORIGIN_REGEX", raising=False)
    else:
        monkeypatch.setenv("ALLOWED_ORIGIN_REGEX", regex)

    import backend.app.main as main_mod
    importlib.reload(main_mod)
    return TestClient(main_mod.app)


class TestDefaultOriginRegex:
    """Default regex permits localhost and *.vercel.app."""

    def test_localhost_allowed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_localhost_no_port_allowed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://localhost"})
        assert r.headers.get("access-control-allow-origin") == "http://localhost"

    def test_vercel_subdomain_allowed(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "https://job-mcp.vercel.app"})
        assert r.headers.get("access-control-allow-origin") == "https://job-mcp.vercel.app"

    def test_arbitrary_origin_rejected(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "https://evil.example.com"})
        # Endpoint still works (CORS is a browser concern), but no CORS header is sent.
        assert r.status_code == 200
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}

    def test_http_non_localhost_rejected(self, monkeypatch):
        client = _client_with_regex(monkeypatch, None)
        r = client.get("/", headers={"Origin": "http://example.com"})
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


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
    import backend.app.main as main_mod
    importlib.reload(main_mod)
