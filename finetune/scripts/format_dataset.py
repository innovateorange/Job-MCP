#!/usr/bin/env python3
"""
Dataset Format Converter — Job-MCP Fine-Tuning
================================================
Converts the JSONL chat-format training data into formats required by
different fine-tuning frameworks:

  - chat     : OpenAI chat format (default, used by Unsloth / Axolotl)
  - alpaca   : instruction/input/output (used by Alpaca-LoRA, LLaMA-Factory)
  - sharegpt : ShareGPT multi-turn (used by Axolotl, FastChat)
  - hf       : Hugging Face datasets format with train/test split

Usage:
    python format_dataset.py --input finetune/data/extraction_train.jsonl \
                             --format alpaca \
                             --output finetune/data/extraction_alpaca.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _save_jsonl(data: list[dict], path: str):
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"✓ Saved {len(data)} examples → {path}")


# ── Format converters ──────────────────────────────────────────────────

def to_chat(examples: list[dict]) -> list[dict]:
    """Already in chat format — pass through."""
    return examples


def to_alpaca(examples: list[dict]) -> list[dict]:
    """Convert chat messages → Alpaca instruction/input/output format."""
    alpaca = []
    for ex in examples:
        msgs = ex.get("messages", [])
        system = ""
        user = ""
        assistant = ""
        for m in msgs:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                user = m["content"]
            elif m["role"] == "assistant":
                assistant = m["content"]

        alpaca.append({
            "instruction": system,
            "input": user,
            "output": assistant,
        })
    return alpaca


def to_sharegpt(examples: list[dict]) -> list[dict]:
    """Convert to ShareGPT format (used by Axolotl / FastChat)."""
    sharegpt = []
    for ex in examples:
        msgs = ex.get("messages", [])
        conversations = []
        for m in msgs:
            role_map = {"system": "system", "user": "human", "assistant": "gpt"}
            conversations.append({
                "from": role_map.get(m["role"], m["role"]),
                "value": m["content"],
            })
        sharegpt.append({"conversations": conversations})
    return sharegpt


def to_hf_dataset(examples: list[dict], output_dir: str):
    """Save as Hugging Face datasets-compatible directory with arrow files."""
    try:
        from datasets import Dataset
    except ImportError:
        print("Install 'datasets' package: pip install datasets")
        return

    # Flatten messages into text column for training
    rows = []
    for ex in examples:
        msgs = ex.get("messages", [])
        # Build a single text column with chat template tokens
        parts = []
        for m in msgs:
            role = m["role"]
            content = m["content"]
            parts.append(f"<|{role}|>\n{content}")
        parts.append("<|assistant|>")  # for generation
        text = "\n".join(parts)
        rows.append({"text": text, "messages": msgs})

    ds = Dataset.from_list(rows)
    ds.save_to_disk(output_dir)
    print(f"✓ Saved HF dataset ({len(rows)} rows) → {output_dir}")


FORMATTERS = {
    "chat": to_chat,
    "alpaca": to_alpaca,
    "sharegpt": to_sharegpt,
}


def main():
    parser = argparse.ArgumentParser(description="Convert training data formats")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--format", choices=["chat", "alpaca", "sharegpt", "hf"],
                        default="chat", help="Target format")
    parser.add_argument("--output", default=None, help="Output path (auto-generated if omitted)")
    args = parser.parse_args()

    examples = _load_jsonl(args.input)
    print(f"Loaded {len(examples)} examples from {args.input}")

    input_path = Path(args.input)

    if args.format == "hf":
        out = args.output or str(input_path.parent / f"{input_path.stem}_hf")
        to_hf_dataset(examples, out)
    else:
        converted = FORMATTERS[args.format](examples)
        out = args.output or str(input_path.parent / f"{input_path.stem}_{args.format}.jsonl")
        _save_jsonl(converted, out)


if __name__ == "__main__":
    main()
