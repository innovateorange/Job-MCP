"""
Tests for the LangChain-based resume processor and chains.

Run:
    pytest backend/tests/test_resume_processor.py -v
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.services.resume_processor import (
    clean_text,
    extract_contact_info,
    extract_raw_text,
)


# ── Unit tests (no LLM needed) ─────────────────────────────────────────

class TestCleanText:
    def test_removes_extra_whitespace(self):
        assert clean_text("hello   world") == "hello world"

    def test_removes_special_chars(self):
        assert "resume" in clean_text("~resume~")

    def test_handles_none(self):
        assert clean_text(None) == ""

    def test_handles_empty(self):
        assert clean_text("") == ""


class TestExtractContactInfo:
    def test_extracts_email(self):
        info = extract_contact_info("Contact me at alice@example.com for more")
        assert info["email"] == "alice@example.com"

    def test_extracts_phone(self):
        info = extract_contact_info("Call (555) 123-4567")
        assert info["phone"] == "(555) 123-4567"

    def test_no_info(self):
        info = extract_contact_info("No contact info here")
        assert info == {}


class TestExtractRawText:
    def test_unsupported_format(self):
        assert extract_raw_text("resume.docx") is None

    def test_missing_file(self):
        assert extract_raw_text("/nonexistent/resume.pdf") is None


# ── Integration tests (mock the LLM) ──────────────────────────────────

class TestResumeChain:
    """Test that the resume chain wires together correctly with a mocked LLM."""

    def test_chain_builds(self):
        """Chain should build without errors when given a mock LLM."""
        from backend.app.chains.resume_chain import build_resume_chain

        mock_llm = MagicMock()
        chain = build_resume_chain(llm=mock_llm)
        assert chain is not None

    def test_skill_chain_builds(self):
        from backend.app.chains.skill_chain import build_skill_chain

        mock_llm = MagicMock()
        chain = build_skill_chain(llm=mock_llm)
        assert chain is not None

    def test_job_match_chain_builds(self):
        from backend.app.chains.job_match_chain import build_job_match_chain

        mock_llm = MagicMock()
        chain = build_job_match_chain(llm=mock_llm)
        assert chain is not None

    def test_cover_letter_chain_builds(self):
        from backend.app.chains.cover_letter_chain import build_cover_letter_chain

        mock_llm = MagicMock()
        chain = build_cover_letter_chain(llm=mock_llm)
        assert chain is not None


class TestLLMProvider:
    """Test the provider factory."""

    def test_unknown_provider_raises(self):
        from backend.app.services.llm_provider import get_llm

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm(provider="nonexistent_provider")

    def test_missing_env_raises(self):
        from backend.app.services.llm_provider import get_llm
        import os

        # Ensure the key is not set
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(ValueError, match="Missing required"):
            get_llm(provider="anthropic")
