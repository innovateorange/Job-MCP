"""
Tests for the FastAPI lifespan startup probe (#48).

Verifies that:
  - The probe is skipped when STARTUP_PROBE_SKIP=1 (the test default).
  - The probe runs when STARTUP_PROBE_SKIP=0.
  - A probe failure causes lifespan startup to raise.
"""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _reload_main():
    from backend.app import main as main_mod
    importlib.reload(main_mod)
    return main_mod


def test_probe_skipped_when_flag_set(monkeypatch):
    monkeypatch.setenv("STARTUP_PROBE_SKIP", "1")
    get_settings.cache_clear()
    main_mod = _reload_main()

    # Patch after reload so the substitute is what lifespan resolves.
    with patch.object(main_mod, "run_startup_probe", new=AsyncMock()) as probe:
        with TestClient(main_mod.app):
            pass
        probe.assert_not_called()


def test_probe_runs_when_flag_unset(monkeypatch):
    monkeypatch.setenv("STARTUP_PROBE_SKIP", "0")
    get_settings.cache_clear()
    main_mod = _reload_main()

    with patch.object(main_mod, "run_startup_probe", new=AsyncMock()) as probe:
        with TestClient(main_mod.app):
            pass
        probe.assert_called_once()


def test_probe_failure_aborts_startup(monkeypatch):
    monkeypatch.setenv("STARTUP_PROBE_SKIP", "0")
    get_settings.cache_clear()
    main_mod = _reload_main()

    boom = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(main_mod, "run_startup_probe", new=boom):
        with pytest.raises(RuntimeError, match="boom"):
            with TestClient(main_mod.app):
                pass
