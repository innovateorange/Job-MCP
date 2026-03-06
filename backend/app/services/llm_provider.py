"""
LLM Provider Factory — Job-MCP Project
========================================
Provider-agnostic LLM initialization using LangChain.

Supports:
  - Custom fine-tuned model (default) via OpenAI-compatible endpoint
  - Anthropic Claude
  - OpenAI / Azure OpenAI
  - HuggingFace Hub / local HF models
  - Ollama (local)
  - Any OpenAI-compatible API (vLLM, Together, Groq, etc.)

Configuration is driven entirely by environment variables so users can
swap providers without touching code.

Env vars
--------
LLM_PROVIDER          : "custom" | "anthropic" | "openai" | "huggingface"
                         | "ollama" | "openai_compatible"   (default: "custom")
LLM_MODEL             : Model name / path  (default: provider-specific)
LLM_TEMPERATURE       : Float 0-2          (default: 0.0)
LLM_MAX_TOKENS        : Int                (default: 4096)

Provider-specific:
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
  HUGGINGFACE_API_TOKEN, HUGGINGFACE_ENDPOINT_URL
  OLLAMA_BASE_URL      (default: http://localhost:11434)
  CUSTOM_LLM_BASE_URL  (for fine-tuned model or any OpenAI-compatible server)
  CUSTOM_LLM_API_KEY   (optional — some endpoints don't require one)
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from langchain_core.language_models import BaseChatModel


class LLMProvider(str, Enum):
    CUSTOM = "custom"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


def _env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(f"Missing required environment variable: {key}")
    return val


# ── Provider-specific builders ──────────────────────────────────────────

def _build_custom(**kwargs) -> BaseChatModel:
    """Custom fine-tuned model served behind an OpenAI-compatible endpoint
    (e.g. vLLM, TGI, or a hosted fine-tune on Together/Fireworks)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=_require_env("CUSTOM_LLM_BASE_URL"),
        api_key=_env("CUSTOM_LLM_API_KEY", "not-needed"),
        model=_env("LLM_MODEL", "fine-tuned-job-mcp"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        max_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


def _build_anthropic(**kwargs) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        api_key=_require_env("ANTHROPIC_API_KEY"),
        model=_env("LLM_MODEL", "claude-sonnet-4-20250514"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        max_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


def _build_openai(**kwargs) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=_require_env("OPENAI_API_KEY"),
        model=_env("LLM_MODEL", "gpt-4o"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        max_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


def _build_azure_openai(**kwargs) -> BaseChatModel:
    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_endpoint=_require_env("AZURE_OPENAI_ENDPOINT"),
        api_key=_require_env("AZURE_OPENAI_API_KEY"),
        azure_deployment=_require_env("AZURE_OPENAI_DEPLOYMENT"),
        api_version=_env("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        max_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


def _build_huggingface(**kwargs) -> BaseChatModel:
    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

    endpoint_url = _env("HUGGINGFACE_ENDPOINT_URL")
    model_name = _env("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

    if endpoint_url:
        # Dedicated Inference Endpoint
        llm = HuggingFaceEndpoint(
            endpoint_url=endpoint_url,
            huggingfacehub_api_token=_require_env("HUGGINGFACE_API_TOKEN"),
            max_new_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
            temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0.01"))),
        )
    else:
        # Serverless Inference API
        llm = HuggingFaceEndpoint(
            repo_id=model_name,
            huggingfacehub_api_token=_require_env("HUGGINGFACE_API_TOKEN"),
            max_new_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
            temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0.01"))),
        )

    return ChatHuggingFace(llm=llm)


def _build_ollama(**kwargs) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=_env("LLM_MODEL", "llama3"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        num_predict=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


def _build_openai_compatible(**kwargs) -> BaseChatModel:
    """Any OpenAI-compatible endpoint (Groq, Together, Fireworks, etc.)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=_require_env("CUSTOM_LLM_BASE_URL"),
        api_key=_require_env("CUSTOM_LLM_API_KEY"),
        model=_env("LLM_MODEL", "default"),
        temperature=kwargs.get("temperature", float(_env("LLM_TEMPERATURE", "0"))),
        max_tokens=kwargs.get("max_tokens", int(_env("LLM_MAX_TOKENS", "4096"))),
    )


# ── Registry ────────────────────────────────────────────────────────────

_BUILDERS = {
    LLMProvider.CUSTOM: _build_custom,
    LLMProvider.ANTHROPIC: _build_anthropic,
    LLMProvider.OPENAI: _build_openai,
    LLMProvider.AZURE_OPENAI: _build_azure_openai,
    LLMProvider.HUGGINGFACE: _build_huggingface,
    LLMProvider.OLLAMA: _build_ollama,
    LLMProvider.OPENAI_COMPATIBLE: _build_openai_compatible,
}


# ── Public API ──────────────────────────────────────────────────────────

def get_llm(
    provider: Optional[str] = None,
    **kwargs,
) -> BaseChatModel:
    """
    Return a LangChain chat model for the requested (or default) provider.

    Parameters
    ----------
    provider : str | None
        Override the LLM_PROVIDER env var for this call.
    **kwargs
        Forwarded to the provider builder (temperature, max_tokens, etc.).
    """
    provider_name = (provider or _env("LLM_PROVIDER", "custom")).lower()

    try:
        provider_enum = LLMProvider(provider_name)
    except ValueError:
        supported = ", ".join(p.value for p in LLMProvider)
        raise ValueError(
            f"Unknown LLM provider '{provider_name}'. "
            f"Supported providers: {supported}"
        )

    builder = _BUILDERS[provider_enum]
    return builder(**kwargs)


@lru_cache(maxsize=1)
def get_default_llm() -> BaseChatModel:
    """Cached singleton for the default LLM (uses LLM_PROVIDER env var)."""
    return get_llm()
