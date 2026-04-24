#!/usr/bin/env python3
"""
Merge LoRA Adapter → Standalone Model
=======================================
Merges a LoRA adapter back into its base model to produce a single
deployable model (no adapter overhead at inference).

Also supports exporting to:
  - HuggingFace format (default)
  - GGUF (for llama.cpp / Ollama)
  - vLLM-ready format

Usage:
    python merge_and_export.py \
        --adapter-path outputs/extraction-lora \
        --output-path outputs/extraction-merged

    # Export to GGUF (requires llama.cpp):
    python merge_and_export.py \
        --adapter-path outputs/extraction-lora \
        --output-path outputs/extraction-gguf \
        --export-format gguf \
        --quantization q4_k_m
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import torch
from peft import PeftModel, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge_adapter(adapter_path: str, output_path: str, dtype: str = "bf16"):
    """Merge LoRA adapter weights into base model."""
    print(f"Loading adapter config from {adapter_path}...")
    config = PeftConfig.from_pretrained(adapter_path)
    base_model_name = config.base_model_name_or_path

    print(f"Loading base model: {base_model_name}...")
    torch_dtype = torch.bfloat16 if dtype == "bf16" else torch.float16

    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)

    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, adapter_path)

    print("Merging weights...")
    model = model.merge_and_unload()

    print(f"Saving merged model → {output_path}")
    os.makedirs(output_path, exist_ok=True)
    model.save_pretrained(output_path, safe_serialization=True)
    tokenizer.save_pretrained(output_path)

    # Save metadata
    metadata = {
        "base_model": base_model_name,
        "adapter_path": adapter_path,
        "merged": True,
        "dtype": dtype,
        "task": _detect_task(adapter_path),
    }
    with open(os.path.join(output_path, "job_mcp_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print("✓ Merge complete!")
    return output_path


def export_gguf(merged_path: str, output_path: str, quantization: str = "q4_k_m"):
    """Export to GGUF format using llama.cpp's convert script."""
    print(f"Exporting to GGUF ({quantization})...")

    # Try to find llama.cpp convert script
    convert_script = shutil.which("convert-hf-to-gguf.py")
    if not convert_script:
        # Common locations
        for loc in ["./llama.cpp/convert-hf-to-gguf.py", "../llama.cpp/convert-hf-to-gguf.py"]:
            if Path(loc).exists():
                convert_script = loc
                break

    if not convert_script:
        print("⚠ llama.cpp convert script not found.")
        print("  Install llama.cpp and ensure convert-hf-to-gguf.py is in PATH.")
        print("  Or run manually:")
        print(f"    python convert-hf-to-gguf.py {merged_path} --outtype {quantization} --outfile {output_path}")
        return

    os.makedirs(Path(output_path).parent, exist_ok=True)
    os.system(f"python {convert_script} {merged_path} --outtype {quantization} --outfile {output_path}")
    print(f"✓ GGUF exported → {output_path}")


def _detect_task(adapter_path: str) -> str:
    """Guess the task from the adapter path name."""
    p = adapter_path.lower()
    if "extraction" in p:
        return "extraction"
    elif "cover" in p:
        return "cover_letter"
    elif "resume" in p or "writer" in p:
        return "resume_writer"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapter and export")
    parser.add_argument("--adapter-path", required=True, help="Path to LoRA adapter directory")
    parser.add_argument("--output-path", required=True, help="Path for merged output")
    parser.add_argument("--dtype", choices=["bf16", "fp16"], default="bf16")
    parser.add_argument("--export-format", choices=["hf", "gguf"], default="hf",
                        help="Export format (hf = HuggingFace safetensors, gguf = llama.cpp)")
    parser.add_argument("--quantization", default="q4_k_m",
                        help="GGUF quantization type (e.g. q4_k_m, q5_k_m, q8_0)")
    args = parser.parse_args()

    merged_path = merge_adapter(args.adapter_path, args.output_path, args.dtype)

    if args.export_format == "gguf":
        gguf_path = args.output_path.rstrip("/") + f".{args.quantization}.gguf"
        export_gguf(merged_path, gguf_path, args.quantization)


if __name__ == "__main__":
    main()
