#!/usr/bin/env python3
"""
Model Server — Job-MCP Fine-Tuned Models
==========================================
Convenience wrapper to launch a fine-tuned model behind an
OpenAI-compatible API (for Job-MCP's CUSTOM_LLM_BASE_URL).

Supports:
  - vLLM (recommended for production)
  - HuggingFace TGI
  - Ollama (via GGUF import)

Usage:
    # Serve merged model via vLLM
    python serve_model.py --model-path outputs/extraction-merged --port 8080

    # Serve LoRA adapter on top of base model (vLLM supports this natively)
    python serve_model.py --model-path meta-llama/Meta-Llama-3.1-8B-Instruct \
        --lora-path outputs/extraction-lora --port 8080

    # Import GGUF into Ollama
    python serve_model.py --model-path outputs/model.q4_k_m.gguf \
        --backend ollama --model-name job-mcp-extraction
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def serve_vllm(args):
    """Launch vLLM OpenAI-compatible server."""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", args.model_path,
        "--port", str(args.port),
        "--host", args.host,
        "--max-model-len", str(args.max_model_len),
        "--dtype", args.dtype,
    ]

    if args.lora_path:
        cmd += ["--enable-lora", "--lora-modules", f"job-mcp={args.lora_path}"]

    if args.tensor_parallel > 1:
        cmd += ["--tensor-parallel-size", str(args.tensor_parallel)]

    if args.gpu_memory_utilization:
        cmd += ["--gpu-memory-utilization", str(args.gpu_memory_utilization)]

    if args.quantization:
        cmd += ["--quantization", args.quantization]

    print(f"Starting vLLM server...")
    print(f"  Model:  {args.model_path}")
    print(f"  LoRA:   {args.lora_path or 'none'}")
    print(f"  Port:   {args.port}")
    print(f"  URL:    http://{args.host}:{args.port}/v1")
    print()
    print("Set these in your .env:")
    print(f"  CUSTOM_LLM_BASE_URL=http://{args.host}:{args.port}/v1")
    print(f"  LLM_MODEL={os.path.basename(args.model_path)}")
    print()

    subprocess.run(cmd)


def serve_tgi(args):
    """Launch HuggingFace Text Generation Inference."""
    cmd = [
        "text-generation-launcher",
        "--model-id", args.model_path,
        "--port", str(args.port),
        "--hostname", args.host,
        "--max-input-length", str(args.max_model_len),
        "--max-total-tokens", str(args.max_model_len + 4096),
    ]

    if args.quantization:
        cmd += ["--quantize", args.quantization]

    if args.tensor_parallel > 1:
        cmd += ["--num-shard", str(args.tensor_parallel)]

    print(f"Starting TGI server...")
    print(f"  Model: {args.model_path}")
    print(f"  Port:  {args.port}")
    print()

    subprocess.run(cmd)


def serve_ollama(args):
    """Import GGUF model into Ollama and serve."""
    model_name = args.model_name or "job-mcp-custom"

    # Create Modelfile
    modelfile_content = f"""FROM {args.model_path}

PARAMETER temperature 0
PARAMETER num_predict 4096

SYSTEM You are an expert AI assistant for job applications. You parse resumes, write cover letters, and improve resumes. Always respond with valid JSON when asked to do so.
"""
    modelfile_path = "/tmp/job_mcp_Modelfile"
    with open(modelfile_path, "w") as f:
        f.write(modelfile_content)

    print(f"Creating Ollama model '{model_name}'...")
    subprocess.run(["ollama", "create", model_name, "-f", modelfile_path])

    print(f"\n✓ Model created. Run with:")
    print(f"  ollama serve  (if not already running)")
    print(f"  ollama run {model_name}")
    print()
    print("Set these in your .env:")
    print(f"  LLM_PROVIDER=ollama")
    print(f"  LLM_MODEL={model_name}")
    print(f"  OLLAMA_BASE_URL=http://localhost:11434")


BACKENDS = {
    "vllm": serve_vllm,
    "tgi": serve_tgi,
    "ollama": serve_ollama,
}


def main():
    parser = argparse.ArgumentParser(description="Serve fine-tuned Job-MCP model")
    parser.add_argument("--model-path", required=True, help="Model or GGUF path")
    parser.add_argument("--lora-path", default=None, help="LoRA adapter path (vLLM only)")
    parser.add_argument("--backend", choices=list(BACKENDS.keys()), default="vllm")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--tensor-parallel", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=None)
    parser.add_argument("--quantization", default=None, help="awq, gptq, squeezellm, etc.")
    parser.add_argument("--model-name", default=None, help="Name for Ollama model")
    args = parser.parse_args()

    BACKENDS[args.backend](args)


if __name__ == "__main__":
    main()
