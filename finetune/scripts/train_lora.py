#!/usr/bin/env python3
"""
LoRA Fine-Tuning Script — Job-MCP
===================================
Fine-tunes a base model using LoRA (Low-Rank Adaptation) with Unsloth
for 2-4x faster training, or falls back to standard PEFT/Transformers.

Supports:
  - Unsloth (recommended, 2x+ faster, less VRAM)
  - Standard PEFT + Transformers Trainer
  - QLoRA (4-bit quantised base model)
  - Multi-GPU via DeepSpeed / FSDP

Usage:
    python train_lora.py --config finetune/configs/lora_extraction.yaml

    # Or override config values via CLI:
    python train_lora.py --config finetune/configs/lora_extraction.yaml \
        --base-model meta-llama/Meta-Llama-3.1-8B-Instruct \
        --epochs 5 \
        --batch-size 4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml


def load_config(config_path: str, overrides: dict) -> dict:
    """Load YAML config and apply CLI overrides."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Apply CLI overrides (only non-None values)
    key_map = {
        "base_model": "base_model",
        "epochs": "num_epochs",
        "batch_size": "per_device_train_batch_size",
        "lr": "learning_rate",
        "lora_r": "lora_r",
        "lora_alpha": "lora_alpha",
        "output_dir": "output_dir",
        "train_data": "train_data",
        "val_data": "val_data",
    }
    for cli_key, cfg_key in key_map.items():
        if cli_key in overrides and overrides[cli_key] is not None:
            cfg[cfg_key] = overrides[cli_key]

    return cfg


def load_dataset(path: str) -> list[dict]:
    """Load JSONL chat-format dataset."""
    data = []
    with open(path) as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def format_chat_for_training(examples: list[dict], tokenizer) -> list[str]:
    """Apply the tokenizer's chat template to produce formatted strings."""
    formatted = []
    for ex in examples:
        msgs = ex.get("messages", [])
        # Use tokenizer's built-in chat template if available
        if hasattr(tokenizer, "apply_chat_template"):
            text = tokenizer.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=False
            )
        else:
            # Fallback: manual chatml format
            parts = []
            for m in msgs:
                parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
            text = "\n".join(parts)
        formatted.append(text)
    return formatted


def train_with_unsloth(cfg: dict):
    """Fine-tune using Unsloth (fast LoRA)."""
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments
    from datasets import Dataset

    print(f"Loading base model: {cfg['base_model']}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["base_model"],
        max_seq_length=cfg.get("max_seq_length", 4096),
        dtype=None,  # auto-detect
        load_in_4bit=cfg.get("quantize_4bit", True),
    )

    # Apply LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=cfg.get("lora_r", 32),
        target_modules=cfg.get("target_modules", [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]),
        lora_alpha=cfg.get("lora_alpha", 64),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    # Load and format data
    print("Loading training data...")
    train_raw = load_dataset(cfg["train_data"])
    train_texts = format_chat_for_training(train_raw, tokenizer)
    train_ds = Dataset.from_dict({"text": train_texts})

    val_ds = None
    if cfg.get("val_data") and Path(cfg["val_data"]).exists():
        val_raw = load_dataset(cfg["val_data"])
        val_texts = format_chat_for_training(val_raw, tokenizer)
        val_ds = Dataset.from_dict({"text": val_texts})

    print(f"Train: {len(train_ds)} examples, Val: {len(val_ds) if val_ds else 0}")

    # Training
    output_dir = cfg.get("output_dir", "outputs/lora-adapter")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        dataset_text_field="text",
        max_seq_length=cfg.get("max_seq_length", 4096),
        packing=cfg.get("packing", True),
        args=TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=cfg.get("num_epochs", 3),
            per_device_train_batch_size=cfg.get("per_device_train_batch_size", 4),
            per_device_eval_batch_size=cfg.get("per_device_eval_batch_size", 4),
            gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 4),
            learning_rate=cfg.get("learning_rate", 2e-4),
            weight_decay=cfg.get("weight_decay", 0.01),
            warmup_ratio=cfg.get("warmup_ratio", 0.05),
            lr_scheduler_type=cfg.get("lr_scheduler", "cosine"),
            logging_steps=cfg.get("logging_steps", 10),
            save_steps=cfg.get("save_steps", 100),
            eval_strategy="steps" if val_ds else "no",
            eval_steps=cfg.get("eval_steps", 100) if val_ds else None,
            save_total_limit=3,
            fp16=not cfg.get("bf16", True),
            bf16=cfg.get("bf16", True),
            seed=cfg.get("seed", 42),
            report_to=cfg.get("report_to", "none"),
        ),
    )

    print("\nStarting training...")
    trainer.train()

    # Save adapter
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\n✓ LoRA adapter saved → {output_dir}")


def train_with_peft(cfg: dict):
    """Fallback: Fine-tune using standard PEFT + Transformers."""
    import torch
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, TrainingArguments, BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer
    from datasets import Dataset

    print(f"Loading base model: {cfg['base_model']}...")

    quantization_config = None
    if cfg.get("quantize_4bit", True):
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"],
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if cfg.get("quantize_4bit"):
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=cfg.get("lora_r", 32),
        lora_alpha=cfg.get("lora_alpha", 64),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        target_modules=cfg.get("target_modules", [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Data
    train_raw = load_dataset(cfg["train_data"])
    train_texts = format_chat_for_training(train_raw, tokenizer)
    train_ds = Dataset.from_dict({"text": train_texts})

    val_ds = None
    if cfg.get("val_data") and Path(cfg["val_data"]).exists():
        val_raw = load_dataset(cfg["val_data"])
        val_texts = format_chat_for_training(val_raw, tokenizer)
        val_ds = Dataset.from_dict({"text": val_texts})

    output_dir = cfg.get("output_dir", "outputs/lora-adapter")

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
            per_device_train_batch_size=cfg.get("per_device_train_batch_size", 4),
            per_device_eval_batch_size=cfg.get("per_device_eval_batch_size", 4),
            gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 4),
            learning_rate=cfg.get("learning_rate", 2e-4),
            weight_decay=cfg.get("weight_decay", 0.01),
            warmup_ratio=cfg.get("warmup_ratio", 0.05),
            lr_scheduler_type=cfg.get("lr_scheduler", "cosine"),
            logging_steps=cfg.get("logging_steps", 10),
            save_steps=cfg.get("save_steps", 100),
            eval_strategy="steps" if val_ds else "no",
            eval_steps=cfg.get("eval_steps", 100) if val_ds else None,
            save_total_limit=3,
            fp16=not cfg.get("bf16", True),
            bf16=cfg.get("bf16", True),
            seed=cfg.get("seed", 42),
            report_to=cfg.get("report_to", "none"),
        ),
    )

    print("\nStarting training...")
    trainer.train()

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\n✓ LoRA adapter saved → {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="LoRA fine-tune for Job-MCP")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--lora-r", type=int, default=None)
    parser.add_argument("--lora-alpha", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--train-data", default=None)
    parser.add_argument("--val-data", default=None)
    parser.add_argument("--backend", choices=["unsloth", "peft"], default="unsloth",
                        help="Training backend")
    args = parser.parse_args()

    cfg = load_config(args.config, vars(args))

    print("=" * 60)
    print("Job-MCP LoRA Fine-Tuning")
    print("=" * 60)
    print(f"  Base model:  {cfg.get('base_model')}")
    print(f"  Train data:  {cfg.get('train_data')}")
    print(f"  LoRA r:      {cfg.get('lora_r')}")
    print(f"  Epochs:      {cfg.get('num_epochs')}")
    print(f"  Batch size:  {cfg.get('per_device_train_batch_size')}")
    print(f"  Output:      {cfg.get('output_dir')}")
    print(f"  Backend:     {args.backend}")
    print("=" * 60)

    if args.backend == "unsloth":
        try:
            import unsloth  # noqa
            train_with_unsloth(cfg)
        except ImportError:
            print("⚠ Unsloth not installed, falling back to PEFT...")
            train_with_peft(cfg)
    else:
        train_with_peft(cfg)


if __name__ == "__main__":
    main()
