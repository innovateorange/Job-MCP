"""
Tests for backend.app.config.Settings (#48).

Verifies:
  - Defaults are usable in dev (no required vars beyond what has defaults).
  - LLM_PROVIDER selecting a hosted backend without its credentials raises.
  - Custom and ollama providers do NOT require keys.
  - Misspelled keys surface clearly via the validator message.
  - get_settings() is cached (returns same instance).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.config import Settings, get_settings


def _build(**overrides) -> Settings:
    """Construct a Settings without reading the on-disk .env file."""
    return Settings(_env_file=None, **overrides)


class TestDefaults:
    def test_defaults_construct(self):
        s = _build()
        assert s.llm_provider == "custom"
        assert s.redis_url.startswith("redis://")
        # startup_probe_skip is set to "1" by conftest.py for the test session,
        # so we just confirm it parsed to a boolean either way.
        assert isinstance(s.startup_probe_skip, bool)

    def test_custom_provider_needs_no_credentials(self):
        # Custom provider has dummy defaults; should not raise.
        s = _build(llm_provider="custom")
        assert s.custom_llm_api_key == "not-needed"

    def test_ollama_needs_no_credentials(self):
        s = _build(llm_provider="ollama")
        assert s.llm_provider == "ollama"


class TestProviderValidation:
    def test_anthropic_without_key_raises(self):
        with pytest.raises(ValidationError) as exc:
            _build(llm_provider="anthropic", anthropic_api_key=None)
        assert "ANTHROPIC_API_KEY" in str(exc.value)

    def test_anthropic_with_key_ok(self):
        s = _build(llm_provider="anthropic", anthropic_api_key="sk-ant-x")
        assert s.anthropic_api_key == "sk-ant-x"

    def test_openai_without_key_raises(self):
        with pytest.raises(ValidationError) as exc:
            _build(llm_provider="openai", openai_api_key=None)
        assert "OPENAI_API_KEY" in str(exc.value)

    def test_azure_partial_credentials_raises(self):
        with pytest.raises(ValidationError) as exc:
            _build(
                llm_provider="azure_openai",
                azure_openai_endpoint="https://x.openai.azure.com",
                # missing key + deployment
            )
        msg = str(exc.value)
        assert "AZURE_OPENAI_API_KEY" in msg
        assert "AZURE_OPENAI_DEPLOYMENT" in msg

    def test_azure_full_credentials_ok(self):
        s = _build(
            llm_provider="azure_openai",
            azure_openai_endpoint="https://x.openai.azure.com",
            azure_openai_api_key="key",
            azure_openai_deployment="gpt-4o",
        )
        assert s.llm_provider == "azure_openai"

    def test_huggingface_without_token_raises(self):
        with pytest.raises(ValidationError) as exc:
            _build(llm_provider="huggingface", huggingface_api_token=None)
        assert "HUGGINGFACE_API_TOKEN" in str(exc.value)

    def test_provider_case_insensitive(self):
        # Validator should accept "ANTHROPIC" or mixed case from env.
        with pytest.raises(ValidationError):
            _build(llm_provider="ANTHROPIC", anthropic_api_key=None)


class TestSupabaseCredentialsHelper:
    def test_prefers_service_role_over_legacy(self):
        s = _build(
            supabase_url="https://x.supabase.co",
            supabase_service_role_key="role",
            supabase_key="legacy",
        )
        url, key = s.supabase_credentials()
        assert url == "https://x.supabase.co"
        assert key == "role"

    def test_falls_back_to_legacy(self):
        s = _build(supabase_url="https://x.supabase.co", supabase_key="legacy")
        _, key = s.supabase_credentials()
        assert key == "legacy"

    def test_returns_none_when_unset(self):
        s = _build()
        assert s.supabase_credentials() == (None, None)


class TestSingletonCache:
    def test_get_settings_returns_same_instance(self):
        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_cache_clear_rebuilds(self):
        get_settings.cache_clear()
        a = get_settings()
        get_settings.cache_clear()
        b = get_settings()
        assert a is not b


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
