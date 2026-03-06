#!/usr/bin/env python3
"""
Full Parameter Fine-Tuning — Job-MCP
======================================
Full fine-tune (no LoRA) for when you want maximum quality and have
sufficient GPU memory / multiple GPUs.

Supports DeepSpeed ZeRO-2/ZeRO-3 for multi-GPU training.

Usage:
    # Single GPU
    python train_full.py --config finetune/configs/full_finetune.yaml

    # Multi-GPU with DeepSpeed
    accelerate launch --config_file ds_config.yaml \
        finetune/scripts/train_full.py --config finetune/configs/full_finetune.yaml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from trl import SFTTrainer
from datasets import Dataset


def load_config(config_path: str, overrides: dict) -> dict:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    for cli_key in ["base_model", "epochs", "batch_size", "lr", "output_dir", "train_data", "val_data"]:
        cfg_key = {
            "epochs": "num_epochs",
            "batch_size": "per_device_train_batch_size",
            "lr": "learning_rate",
        }.get(cli_key, cli_key)
        if cli_key in overrides and overrides[cli_key] is not None:
            cfg[cfg_key] = overrides[cli_key]
    return cfg


def load_dataset_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def format_chat(examples: list[dict], tokenizer) -> list[str]:
    formatted = []
    for ex in examples:
        msgs = ex.get("messages", [])
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        else:
            parts = [f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>" for m in msgs]
            text = "\n".join(parts)
        formatted.append(text)
    return formatted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--train-data", default=None)
    parser.add_argument("--val-data", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config, vars(args))

    print("=" * 60)
    print("Job-MCP Full Fine-Tuning")
    print("=" * 60)
    print(f"  Base model: {cfg['base_model']}")
    print(f"  Epochs:     {cfg.get('num_epochs', 3)}")
    print(f"  Output:     {cfg.get('output_dir')}")
    print("=" * 60)

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"],
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Data
    train_raw = load_dataset_jsonl(cfg["train_data"])
    train_texts = format_chat(train_raw, tokenizer)
    train_ds = Dataset.from_dict({"text": train_texts})

    val_ds = None
    if cfg.get("val_data") and Path(cfg["val_data"]).exists():
        val_raw = load_dataset_jsonl(cfg["val_data"])
        val_texts = format_chat(val_raw, tokenizer)
        val_ds = Dataset.from_dict({"text": val_texts})

    output_dir = cfg.get("output_dir", "outputs/full-finetune")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        dataset_text_field="text",
        max_seq_length=cfg.get("max_seq_length", 4096),
        packing=cfg.get("packing", False),
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=cfg.get("num_epochs", 3),
            per_device_train_batch_size=cfg.get("per_device_train_batch_size", 2),
            per_device_eval_batch_size=cfg.get("per_device_eval_batch_size", 2),
            gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 8),
            learning_rate=cfg.get("learning_rate", 5e-5),
            weight_decay=cfg.get("weight_decay", 0.01),
            warmup_ratio=cfg.get("warmup_ratio", 0.05),
            lr_scheduler_type=cfg.get("lr_scheduler", "cosine"),
            logging_steps=cfg.get("logging_steps", 10),
            save_steps=cfg.get("save_steps", 200),
            eval_strategy="steps" if val_ds else "no",
            eval_steps=cfg.get("eval_steps", 200) if val_ds else None,
            save_total_limit=2,
            bf16=True,
            gradient_checkpointing=True,
            seed=cfg.get("seed", 42),
            report_to=cfg.get("report_to", "none"),
            deepspeed=cfg.get("deepspeed_config", None),
            fsdp=cfg.get("fsdp", ""),
        ),
    )

    print("\nStarting full fine-tuning...")
    trainer.train()

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\n✓ Model saved → {output_dir}")


if __name__ == "__main__":
    main()
