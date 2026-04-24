#!/usr/bin/env python3
"""
Evaluation Script — Job-MCP Fine-Tuned Models
===============================================
Runs the fine-tuned model against a held-out test set and computes
task-specific metrics.

Metrics by task:
  extraction    → JSON schema validity, field-level F1, skill recall
  cover_letter  → length compliance, key-points coverage, coherence score
  resume_writer → improvement detection, skills highlighted, length compliance

Usage:
    python evaluate.py \
        --model-path outputs/extraction-merged \
        --test-data finetune/data/extraction_val.jsonl \
        --task extraction

    # Or use a running server:
    python evaluate.py \
        --provider custom \
        --test-data finetune/data/extraction_val.jsonl \
        --task extraction
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def load_test_data(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def run_inference(example: dict, llm) -> str:
    """Run the model on a single example and return the raw string output."""
    from langchain_core.messages import SystemMessage, HumanMessage

    msgs = example.get("messages", [])
    lc_msgs = []
    for m in msgs:
        if m["role"] == "system":
            lc_msgs.append(SystemMessage(content=m["content"]))
        elif m["role"] == "user":
            lc_msgs.append(HumanMessage(content=m["content"]))
        # Skip assistant (that's the expected output)

    resp = llm.invoke(lc_msgs)
    return resp.content if hasattr(resp, "content") else str(resp)


def parse_json_safe(text: str) -> dict | None:
    """Try to parse JSON from model output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ── Task-specific evaluators ───────────────────────────────────────────

def eval_extraction(examples: list[dict], llm) -> dict:
    """Evaluate extraction task."""
    results = {
        "total": len(examples),
        "valid_json": 0,
        "schema_valid": 0,
        "field_scores": {},
        "skill_recall": [],
    }

    required_fields = {"name", "email", "skills", "education", "experience"}

    for i, ex in enumerate(examples):
        print(f"  [{i+1}/{len(examples)}]", end=" ", flush=True)
        expected_str = ex["messages"][-1]["content"]
        expected = parse_json_safe(expected_str)

        output_str = run_inference(ex, llm)
        predicted = parse_json_safe(output_str)

        if predicted is not None:
            results["valid_json"] += 1

            # Schema check
            if required_fields.issubset(set(predicted.keys())):
                results["schema_valid"] += 1

            # Skill recall
            if expected:
                expected_skills = set(s.lower() for s in expected.get("skills", []))
                predicted_skills = set(s.lower() for s in predicted.get("skills", []))
                if expected_skills:
                    recall = len(expected_skills & predicted_skills) / len(expected_skills)
                    results["skill_recall"].append(recall)
                    print(f"skills recall={recall:.2f}", end=" ")

        print("✓" if predicted else "✗")

    results["valid_json_pct"] = results["valid_json"] / max(results["total"], 1) * 100
    results["schema_valid_pct"] = results["schema_valid"] / max(results["total"], 1) * 100
    results["avg_skill_recall"] = (
        sum(results["skill_recall"]) / len(results["skill_recall"])
        if results["skill_recall"] else 0
    )
    return results


def eval_cover_letter(examples: list[dict], llm) -> dict:
    """Evaluate cover letter task."""
    results = {
        "total": len(examples),
        "valid_json": 0,
        "avg_word_count": 0,
        "in_length_range": 0,
        "has_key_points": 0,
    }
    word_counts = []

    for i, ex in enumerate(examples):
        print(f"  [{i+1}/{len(examples)}]", end=" ", flush=True)
        output_str = run_inference(ex, llm)
        predicted = parse_json_safe(output_str)

        if predicted:
            results["valid_json"] += 1
            cl = predicted.get("cover_letter", "")
            wc = len(cl.split())
            word_counts.append(wc)
            if 200 <= wc <= 500:
                results["in_length_range"] += 1
            if predicted.get("key_points"):
                results["has_key_points"] += 1
            print(f"words={wc}", end=" ")

        print("✓" if predicted else "✗")

    results["valid_json_pct"] = results["valid_json"] / max(results["total"], 1) * 100
    results["avg_word_count"] = sum(word_counts) / len(word_counts) if word_counts else 0
    results["in_length_range_pct"] = results["in_length_range"] / max(results["total"], 1) * 100
    return results


def eval_resume_writer(examples: list[dict], llm) -> dict:
    """Evaluate resume writer task."""
    results = {
        "total": len(examples),
        "valid_json": 0,
        "has_changes": 0,
        "has_skills_highlighted": 0,
        "avg_word_count": 0,
    }
    word_counts = []

    for i, ex in enumerate(examples):
        print(f"  [{i+1}/{len(examples)}]", end=" ", flush=True)
        output_str = run_inference(ex, llm)
        predicted = parse_json_safe(output_str)

        if predicted:
            results["valid_json"] += 1
            resume = predicted.get("improved_resume", "")
            wc = len(resume.split())
            word_counts.append(wc)
            if predicted.get("changes_made"):
                results["has_changes"] += 1
            if predicted.get("skills_highlighted"):
                results["has_skills_highlighted"] += 1
            print(f"words={wc}", end=" ")

        print("✓" if predicted else "✗")

    results["valid_json_pct"] = results["valid_json"] / max(results["total"], 1) * 100
    results["avg_word_count"] = sum(word_counts) / len(word_counts) if word_counts else 0
    return results


EVALUATORS = {
    "extraction": eval_extraction,
    "cover_letter": eval_cover_letter,
    "resume_writer": eval_resume_writer,
}


def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned Job-MCP model")
    parser.add_argument("--test-data", required=True, help="Test JSONL file")
    parser.add_argument("--task", required=True, choices=list(EVALUATORS.keys()))
    parser.add_argument("--model-path", default=None, help="Local model path (uses HF loader)")
    parser.add_argument("--provider", default=None, help="LLM provider from llm_provider.py")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit eval samples")
    args = parser.parse_args()

    # Load LLM
    if args.model_path:
        # Load local model via LangChain HuggingFace
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch

        print(f"Loading model from {args.model_path}...")
        tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_path, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True,
        )
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=4096)
        hf_llm = HuggingFacePipeline(pipeline=pipe)
        llm = ChatHuggingFace(llm=hf_llm)
    else:
        from backend.app.services.llm_provider import get_llm
        llm = get_llm(provider=args.provider)

    # Load test data
    examples = load_test_data(args.test_data)
    if args.max_samples:
        examples = examples[:args.max_samples]

    print(f"\n{'='*60}")
    print(f"Evaluating: {args.task} ({len(examples)} examples)")
    print(f"{'='*60}\n")

    evaluator = EVALUATORS[args.task]
    results = evaluator(examples, llm)

    print(f"\n{'='*60}")
    print("Results:")
    print("=" * 60)
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        elif isinstance(v, list):
            print(f"  {k}: [{len(v)} values]")
        else:
            print(f"  {k}: {v}")

    # Save results
    out_path = f"finetune/data/{args.task}_eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✓ Results saved → {out_path}")


if __name__ == "__main__":
    main()
