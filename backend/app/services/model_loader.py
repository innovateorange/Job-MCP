"""
Fine-Tuned Model Loader — Job-MCP
===================================
Provides functions to load fine-tuned models into the LangChain pipeline,
supporting multiple serving strategies:

  1. **Remote server** — model is already served via vLLM / TGI / Ollama
     behind an OpenAI-compatible endpoint (preferred for production).

  2. **Local HuggingFace** — load model weights directly into GPU memory
     (good for development / single-machine setups).

  3. **LoRA adapter** — load base model + LoRA adapter separately
     (saves disk space, supports hot-swapping adapters).

The loader returns a standard LangChain BaseChatModel that can be passed
to any chain builder (build_resume_chain, build_cover_letter_chain, etc.).

Usage
-----
    from backend.app.services.model_loader import load_finetuned_model

    # From a running vLLM server
    llm = load_finetuned_model(
        method="remote",
        base_url="http://localhost:8080/v1",
        model_name="extraction-merged",
    )

    # From local weights
    llm = load_finetuned_model(
        method="local",
        model_path="outputs/extraction-merged",
    )

    # LoRA adapter on base model
    llm = load_finetuned_model(
        method="lora",
        model_path="meta-llama/Meta-Llama-3.1-8B-Instruct",
        adapter_path="outputs/extraction-lora",
    )

    # Then use it in any chain:
    from backend.app.chains import build_resume_chain
    chain = build_resume_chain(llm=llm)
    result = await chain.ainvoke({"resume_text": "..."})
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from langchain_core.language_models import BaseChatModel


class LoadMethod(str, Enum):
    REMOTE = "remote"
    LOCAL = "local"
    LORA = "lora"


def load_finetuned_model(
    method: str = "remote",
    model_path: Optional[str] = None,
    adapter_path: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    device_map: str = "auto",
    max_tokens: int = 4096,
    temperature: float = 0.0,
    **kwargs,
) -> BaseChatModel:
    """
    Load a fine-tuned model into a LangChain chat model.

    Parameters
    ----------
    method : str
        "remote" — connect to an OpenAI-compatible API server
        "local"  — load HuggingFace model directly into memory
        "lora"   — load base model + LoRA adapter into memory

    model_path : str
        For "local"/"lora": path to model weights or HF repo ID.
        For "remote": ignored (use base_url + model_name).

    adapter_path : str
        For "lora" only: path to the LoRA adapter directory.

    base_url : str
        For "remote": the server URL (e.g. http://localhost:8080/v1).

    model_name : str
        For "remote": the model name to pass in API requests.

    api_key : str
        For "remote": API key if required.

    device_map : str
        For "local"/"lora": device mapping strategy.

    Returns
    -------
    BaseChatModel
        A LangChain chat model ready for use in chains.
    """
    load_method = LoadMethod(method.lower())

    if load_method == LoadMethod.REMOTE:
        return _load_remote(
            base_url=base_url or os.getenv("CUSTOM_LLM_BASE_URL", "http://localhost:8080/v1"),
            model_name=model_name or os.getenv("LLM_MODEL", "fine-tuned-job-mcp"),
            api_key=api_key or os.getenv("CUSTOM_LLM_API_KEY", "not-needed"),
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif load_method == LoadMethod.LOCAL:
        return _load_local(
            model_path=model_path,
            device_map=device_map,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif load_method == LoadMethod.LORA:
        return _load_lora(
            model_path=model_path,
            adapter_path=adapter_path,
            device_map=device_map,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown load method: {method}")


def _load_remote(
    base_url: str,
    model_name: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> BaseChatModel:
    """Connect to an OpenAI-compatible server (vLLM, TGI, etc.)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _load_local(
    model_path: str,
    device_map: str,
    max_tokens: int,
    temperature: float,
) -> BaseChatModel:
    """Load a merged fine-tuned model directly from disk."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

    if not model_path:
        raise ValueError("model_path is required for local loading")

    print(f"Loading fine-tuned model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map=device_map,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_tokens,
        temperature=temperature if temperature > 0 else None,
        do_sample=temperature > 0,
    )

    hf_llm = HuggingFacePipeline(pipeline=pipe)
    return ChatHuggingFace(llm=hf_llm)


def _load_lora(
    model_path: str,
    adapter_path: str,
    device_map: str,
    max_tokens: int,
    temperature: float,
) -> BaseChatModel:
    """Load base model + LoRA adapter without merging (saves memory)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
    from peft import PeftModel
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

    if not model_path or not adapter_path:
        raise ValueError("Both model_path and adapter_path are required for LoRA loading")

    print(f"Loading base model: {model_path}")
    print(f"Loading LoRA adapter: {adapter_path}")

    # Load base in 4-bit for efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Apply LoRA adapter
    model = PeftModel.from_pretrained(base_model, adapter_path)

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_tokens,
        temperature=temperature if temperature > 0 else None,
        do_sample=temperature > 0,
    )

    hf_llm = HuggingFacePipeline(pipeline=pipe)
    return ChatHuggingFace(llm=hf_llm)


# ── Convenience: per-task model loading ────────────────────────────────

# Map task names → env vars for per-task model endpoints
_TASK_ENV_MAP = {
    "extraction": {
        "base_url": "EXTRACTION_MODEL_BASE_URL",
        "model_name": "EXTRACTION_MODEL_NAME",
        "model_path": "EXTRACTION_MODEL_PATH",
        "adapter_path": "EXTRACTION_ADAPTER_PATH",
    },
    "cover_letter": {
        "base_url": "COVER_LETTER_MODEL_BASE_URL",
        "model_name": "COVER_LETTER_MODEL_NAME",
        "model_path": "COVER_LETTER_MODEL_PATH",
        "adapter_path": "COVER_LETTER_ADAPTER_PATH",
    },
    "resume_writer": {
        "base_url": "RESUME_WRITER_MODEL_BASE_URL",
        "model_name": "RESUME_WRITER_MODEL_NAME",
        "model_path": "RESUME_WRITER_MODEL_PATH",
        "adapter_path": "RESUME_WRITER_ADAPTER_PATH",
    },
}


def load_task_model(task: str, method: Optional[str] = None) -> BaseChatModel:
    """
    Load the fine-tuned model for a specific task.

    Checks for task-specific env vars first, then falls back to the
    default LLM_PROVIDER configuration.

    Parameters
    ----------
    task : str
        One of: "extraction", "cover_letter", "resume_writer"
    method : str | None
        Override the load method. If None, auto-detects from env vars.

    Example env setup for per-task models:
        EXTRACTION_MODEL_BASE_URL=http://localhost:8080/v1
        EXTRACTION_MODEL_NAME=extraction-merged
        COVER_LETTER_MODEL_BASE_URL=http://localhost:8081/v1
        COVER_LETTER_MODEL_NAME=cover-letter-merged
    """
    env_map = _TASK_ENV_MAP.get(task, {})

    base_url = os.getenv(env_map.get("base_url", ""))
    model_name = os.getenv(env_map.get("model_name", ""))
    model_path = os.getenv(env_map.get("model_path", ""))
    adapter_path = os.getenv(env_map.get("adapter_path", ""))

    # Auto-detect method
    if method is None:
        if base_url:
            method = "remote"
        elif adapter_path and model_path:
            method = "lora"
        elif model_path:
            method = "local"
        else:
            # Fall back to default provider
            from backend.app.services.llm_provider import get_default_llm
            return get_default_llm()

    return load_finetuned_model(
        method=method,
        model_path=model_path or None,
        adapter_path=adapter_path or None,
        base_url=base_url or None,
        model_name=model_name or None,
    )
