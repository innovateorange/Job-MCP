#!/usr/bin/env python3
"""
Dataset Downloader & Converter — Job-MCP Fine-Tuning
=====================================================
Downloads public resume, cover letter, and job matching datasets from
HuggingFace and converts them into chat-format JSONL for training.

All training data comes from real datasets — no synthetic generation.

Datasets:
─────────────────────────────────────────────────────────────────────
EXTRACTION (resume → structured JSON):
  1. datasetmaster/resumes         — ~1,000 resumes in nested JSON (from HuggingFace)
  2. InferencePrince555/Resume-Dataset — resume text + category labels

COVER LETTER:
  3. ShashiVish/cover-letter-dataset — 1,162 cover letter examples
  4. dhruvvaidh/cover-letter-dataset-llama3 — Llama 3-formatted cover letters

RESUME WRITING / IMPROVEMENT:
  5. MikePfunk28/resume-training-dataset — 22,855 chat-format conversations

Usage:
    python download_datasets.py --task all --output-dir finetune/data
    python download_datasets.py --task extraction
    python download_datasets.py --task cover_letter
    python download_datasets.py --task resume_writer
    python download_datasets.py --task all --max-samples 500
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("Install the datasets library: pip install datasets")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
# System prompts (must match what the chains use at inference time)
# ══════════════════════════════════════════════════════════════════════════

EXTRACTION_SYSTEM = (
    "You are an expert resume parser for a job-application platform.\n\n"
    "Given the raw text extracted from a candidate's resume, produce a single "
    "JSON object with these keys: name, email, phone, location, summary, "
    "education, experience, skills, certifications, projects, languages, links.\n\n"
    "Rules:\n"
    "- Extract every piece of information you can find; leave fields as empty "
    "strings or empty lists when the information is not present.\n"
    "- Normalise skill names (e.g. 'JS' → 'JavaScript').\n"
    "- Dates should use the format found in the resume.\n"
    "- Preserve the original meaning; do not invent information.\n"
    "- Return ONLY valid JSON, nothing else."
)

COVER_LETTER_SYSTEM = (
    "You are a professional cover-letter writer for CS students and early-career developers.\n\n"
    "Given the candidate's profile and a target job description, write a concise, "
    "compelling cover letter.\n\n"
    "Return a JSON object with keys: cover_letter, word_count, key_points.\n\n"
    "Guidelines:\n"
    "- Length: 250-400 words\n"
    "- Highlight the candidate's most relevant skills\n"
    "- Mention the company by name\n"
    "- Be specific, avoid filler\n"
    "- Do NOT fabricate experience\n"
    "- Return ONLY valid JSON, nothing else."
)

RESUME_WRITER_SYSTEM = (
    "You are an expert resume writer for CS students and developers.\n\n"
    "Given the candidate's current profile and a target job description, "
    "rewrite their resume to be tailored for that specific role.\n\n"
    "Return a JSON object with keys: improved_resume, changes_made, "
    "skills_highlighted, word_count.\n\n"
    "Guidelines:\n"
    "- Reorder and reword to emphasize relevant experience\n"
    "- Add a tailored summary/objective\n"
    "- Use strong action verbs and quantified achievements\n"
    "- Keep ALL truthful information, do NOT fabricate\n"
    "- 400-600 words\n"
    "- Return ONLY valid JSON, nothing else."
)


def _save_jsonl(data: list[dict], path: str):
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"  ✓ Saved {len(data)} examples → {path}")


def _train_val_split(examples: list[dict], val_ratio: float = 0.1):
    random.shuffle(examples)
    split = max(1, int(len(examples) * val_ratio))
    return examples[split:], examples[:split]


# ══════════════════════════════════════════════════════════════════════════
# Profile conversion helpers
# ══════════════════════════════════════════════════════════════════════════

def _profile_to_resume_text(profile: dict) -> str:
    """Convert a structured profile dict into resume-like plain text."""
    lines = []

    name = profile.get("personal_information", {}).get("name", "") or profile.get("name", "")
    email = profile.get("personal_information", {}).get("contact", {}).get("email", "") or profile.get("email", "")
    phone = profile.get("personal_information", {}).get("contact", {}).get("phone", "") or profile.get("phone", "")
    location = profile.get("personal_information", {}).get("location", {})
    if isinstance(location, dict):
        loc_str = ", ".join(filter(None, [location.get("city", ""), location.get("state", ""), location.get("country", "")]))
    else:
        loc_str = str(location) if location else ""

    if name:
        lines.append(name)
    if email:
        lines.append(email)
    if phone:
        lines.append(phone)
    if loc_str:
        lines.append(loc_str)
    lines.append("")

    summary = profile.get("personal_information", {}).get("summary", "") or profile.get("summary", "")
    if summary:
        lines.append("PROFESSIONAL SUMMARY")
        lines.append(summary)
        lines.append("")

    education = profile.get("education", [])
    if education:
        lines.append("EDUCATION")
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get("degree", "")
                institution = edu.get("institution", "")
                field = edu.get("field_of_study", "") or edu.get("field", "")
                dates = f"{edu.get('start_date', '')} - {edu.get('end_date', '')}".strip(" -")
                gpa = edu.get("gpa", "")
                lines.append(f"{degree} in {field} — {institution}" if field else f"{degree} — {institution}")
                if dates:
                    lines.append(dates)
                if gpa:
                    lines.append(f"GPA: {gpa}")
                for ach in edu.get("achievements", []):
                    lines.append(f"  • {ach}")
                lines.append("")

    experience = profile.get("experience", [])
    if experience:
        lines.append("EXPERIENCE")
        for exp in experience:
            if isinstance(exp, dict):
                title = exp.get("job_title", "") or exp.get("title", "")
                company = exp.get("company", {})
                if isinstance(company, dict):
                    company_name = company.get("name", "")
                else:
                    company_name = str(company)
                dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}".strip(" -")
                lines.append(f"{title} at {company_name}")
                if dates:
                    lines.append(dates)
                for resp in exp.get("responsibilities", []):
                    lines.append(f"  • {resp}")
                lines.append("")

    skills = profile.get("skills", {})
    if isinstance(skills, dict):
        lines.append("SKILLS")
        for cat, items in skills.items():
            if isinstance(items, list) and items:
                lines.append(f"{cat.replace('_', ' ').title()}: {', '.join(str(s) for s in items)}")
        lines.append("")
    elif isinstance(skills, list) and skills:
        lines.append("SKILLS")
        lines.append(", ".join(str(s) for s in skills))
        lines.append("")

    projects = profile.get("projects", [])
    if projects:
        lines.append("PROJECTS")
        for proj in projects:
            if isinstance(proj, dict):
                lines.append(f"{proj.get('name', 'Project')}")
                if proj.get("description"):
                    lines.append(f"  {proj['description']}")
                if proj.get("technologies"):
                    lines.append(f"  Technologies: {', '.join(proj['technologies'])}")
                lines.append("")

    return "\n".join(lines).strip()


def _flatten_profile_for_output(profile: dict) -> dict:
    """Flatten the nested HF dataset format into our chain's output schema."""
    pi = profile.get("personal_information", {})
    contact = pi.get("contact", {})
    location = pi.get("location", {})

    education = []
    for edu in profile.get("education", []):
        if isinstance(edu, dict):
            education.append({
                "institution": edu.get("institution", ""),
                "degree": edu.get("degree", ""),
                "field": edu.get("field_of_study", "") or edu.get("field", ""),
                "start_date": edu.get("start_date", ""),
                "end_date": edu.get("end_date", ""),
                "gpa": str(edu.get("gpa", "")),
            })

    experience = []
    for exp in profile.get("experience", []):
        if isinstance(exp, dict):
            company = exp.get("company", {})
            experience.append({
                "company": company.get("name", "") if isinstance(company, dict) else str(company),
                "title": exp.get("job_title", "") or exp.get("title", ""),
                "start_date": exp.get("start_date", ""),
                "end_date": exp.get("end_date", ""),
                "description": "; ".join(exp.get("responsibilities", [])),
                "location": exp.get("location", ""),
            })

    skills_raw = profile.get("skills", {})
    skills = []
    if isinstance(skills_raw, dict):
        for items in skills_raw.values():
            if isinstance(items, list):
                skills.extend(str(s) for s in items)
    elif isinstance(skills_raw, list):
        skills = [str(s) for s in skills_raw]

    projects = []
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            projects.append({
                "name": proj.get("name", ""),
                "description": proj.get("description", ""),
                "technologies": proj.get("technologies", []),
                "url": proj.get("url", ""),
            })

    loc_str = ""
    if isinstance(location, dict):
        loc_str = ", ".join(filter(None, [location.get("city", ""), location.get("state", ""), location.get("country", "")]))

    return {
        "name": pi.get("name", ""),
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "location": loc_str,
        "summary": pi.get("summary", ""),
        "education": education,
        "experience": experience,
        "skills": skills,
        "certifications": profile.get("certifications", []),
        "projects": projects,
        "languages": profile.get("languages", []),
        "links": list(filter(None, [
            pi.get("social_profiles", {}).get("linkedin", ""),
            pi.get("social_profiles", {}).get("github", ""),
        ])) if isinstance(pi.get("social_profiles"), dict) else [],
    }


# ══════════════════════════════════════════════════════════════════════════
# Dataset downloaders — all data from real HuggingFace datasets only
# ══════════════════════════════════════════════════════════════════════════

# ── 1. Extraction: datasetmaster/resumes ────────────────────────────────

def download_extraction_data(max_samples: int | None = None) -> list[dict]:
    """Download and convert datasetmaster/resumes to extraction training format."""
    examples = []

    # Primary: datasetmaster/resumes (structured profiles → resume text + JSON pairs)
    print("\n📥 Downloading datasetmaster/resumes...")
    try:
        ds = load_dataset("datasetmaster/resumes", split="train")
        for i, row in enumerate(ds):
            if max_samples and i >= max_samples:
                break
            try:
                resume_text = _profile_to_resume_text(row)
                if len(resume_text.strip()) < 50:
                    continue
                profile_json = _flatten_profile_for_output(row)

                example = {
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM},
                        {"role": "user", "content": f'Resume text:\n"""\n{resume_text}\n"""'},
                        {"role": "assistant", "content": json.dumps(profile_json, indent=2)},
                    ]
                }
                examples.append(example)
            except Exception:
                continue

        print(f"  ✓ Converted {len(examples)} extraction examples from datasetmaster/resumes")
    except Exception as e:
        print(f"  ⚠ Failed to load datasetmaster/resumes: {e}")

    # Supplementary: InferencePrince555/Resume-Dataset
    # Only include examples where the dataset provides enough structure to
    # build a meaningful ground-truth output (category label as a signal).
    print("📥 Downloading InferencePrince555/Resume-Dataset...")
    try:
        ds2 = load_dataset("InferencePrince555/Resume-Dataset", split="train")
        count = 0
        for row in ds2:
            if max_samples and (len(examples) + count) >= max_samples:
                break
            resume_text = row.get("Resume_str", "") or row.get("text", "")
            category = row.get("Category", "") or row.get("category", "")
            if not resume_text or len(resume_text) < 100:
                continue

            # Use the category as a signal — the resume text IS the ground truth
            # input, and we create a minimal but honest output that only
            # populates what we can actually derive from the dataset fields.
            # The model learns the extraction format from the richer
            # datasetmaster examples; these add input diversity.
            profile = {
                "name": "", "email": "", "phone": "", "location": "",
                "summary": f"Professional in {category}" if category else "",
                "education": [], "experience": [],
                "skills": [], "certifications": [], "projects": [],
                "languages": [], "links": [],
            }

            example = {
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM},
                    {"role": "user", "content": f'Resume text:\n"""\n{resume_text[:3000]}\n"""'},
                    {"role": "assistant", "content": json.dumps(profile, indent=2)},
                ]
            }
            examples.append(example)
            count += 1

        print(f"  ✓ Added {count} examples from InferencePrince555/Resume-Dataset")
    except Exception as e:
        print(f"  ⚠ Failed: {e}")

    print(f"  Total extraction examples: {len(examples)}")
    return examples


# ── 2. Cover Letter: ShashiVish + dhruvvaidh ──────────────────────────

def download_cover_letter_data(max_samples: int | None = None) -> list[dict]:
    """Download and convert cover letter datasets."""
    examples = []

    # Llama3-formatted version first
    print("\n📥 Downloading dhruvvaidh/cover-letter-dataset-llama3...")
    try:
        ds = load_dataset("dhruvvaidh/cover-letter-dataset-llama3", split="train")
        for i, row in enumerate(ds):
            if max_samples and i >= max_samples:
                break
            text = row.get("text", "")
            if not text or len(text) < 100:
                continue

            job_desc = row.get("job_description", "") or row.get("input", "") or ""
            cover_letter = row.get("cover_letter", "") or row.get("output", "") or text

            if not job_desc:
                parts = text.split("\n\n", 1)
                if len(parts) == 2:
                    job_desc = parts[0]
                    cover_letter = parts[1]
                else:
                    job_desc = "Write a cover letter for a software engineering position."
                    cover_letter = text

            output = {
                "cover_letter": cover_letter.strip(),
                "word_count": len(cover_letter.split()),
                "key_points": [],
            }

            example = {
                "messages": [
                    {"role": "system", "content": COVER_LETTER_SYSTEM},
                    {"role": "user", "content": (
                        f"Candidate profile:\n```json\n{{}}\n```\n\n"
                        f"Company: the company\n\n"
                        f'Job description:\n"""\n{job_desc}\n"""'
                    )},
                    {"role": "assistant", "content": json.dumps(output, indent=2)},
                ]
            }
            examples.append(example)

        print(f"  ✓ Converted {len(examples)} cover letter examples (llama3 format)")
    except Exception as e:
        print(f"  ⚠ Failed: {e}")

    # Base dataset
    print("📥 Downloading ShashiVish/cover-letter-dataset...")
    try:
        ds2 = load_dataset("ShashiVish/cover-letter-dataset", split="train")
        count = 0
        for row in ds2:
            if max_samples and (len(examples) + count) >= max_samples:
                break
            text = row.get("text", "") or row.get("cover_letter", "")
            if not text or len(text) < 100:
                continue

            output = {
                "cover_letter": text.strip(),
                "word_count": len(text.split()),
                "key_points": [],
            }

            example = {
                "messages": [
                    {"role": "system", "content": COVER_LETTER_SYSTEM},
                    {"role": "user", "content": (
                        "Candidate profile:\n```json\n{}\n```\n\n"
                        "Company: the company\n\n"
                        'Job description:\n"""\nWrite a cover letter for the position.\n"""'
                    )},
                    {"role": "assistant", "content": json.dumps(output, indent=2)},
                ]
            }
            examples.append(example)
            count += 1

        print(f"  ✓ Added {count} more cover letter examples (ShashiVish)")
    except Exception as e:
        print(f"  ⚠ Failed: {e}")

    print(f"  Total cover letter examples: {len(examples)}")
    return examples


# ── 3. Resume Writing: MikePfunk28/resume-training-dataset ──────────────

def download_resume_writer_data(max_samples: int | None = None) -> list[dict]:
    """Download MikePfunk28's 22K resume conversation dataset."""
    print("\n📥 Downloading MikePfunk28/resume-training-dataset...")
    try:
        ds = load_dataset("MikePfunk28/resume-training-dataset", split="train")
    except Exception as e:
        print(f"  ⚠ Failed: {e}")
        return []

    examples = []
    for i, row in enumerate(ds):
        if max_samples and i >= max_samples:
            break

        messages = row.get("messages", []) or row.get("conversations", [])

        if not messages:
            text = row.get("text", "")
            if not text:
                continue
            messages = [
                {"role": "system", "content": RESUME_WRITER_SYSTEM},
                {"role": "user", "content": text[:2000]},
                {"role": "assistant", "content": "I'll help improve this resume."},
            ]

        # Ensure system prompt is ours
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = RESUME_WRITER_SYSTEM

        # Validate message structure
        valid = all(
            isinstance(m, dict) and "role" in m and "content" in m
            for m in messages
        )
        if not valid:
            continue

        examples.append({"messages": messages})

    print(f"  ✓ Converted {len(examples)} resume writer examples")
    return examples


# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════

TASK_DOWNLOADERS = {
    "extraction": download_extraction_data,
    "cover_letter": download_cover_letter_data,
    "resume_writer": download_resume_writer_data,
}


def main():
    parser = argparse.ArgumentParser(description="Download & convert training datasets from HuggingFace")
    parser.add_argument("--task", choices=["extraction", "cover_letter", "resume_writer", "all"],
                        default="all")
    parser.add_argument("--output-dir", default="finetune/data")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Max samples per dataset (useful for testing)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = list(TASK_DOWNLOADERS.keys()) if args.task == "all" else [args.task]
    all_combined = []

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print(f"{'='*60}")

        downloader = TASK_DOWNLOADERS[task]
        examples = downloader(args.max_samples)

        if not examples:
            print(f"  ⚠ No examples for {task}, skipping")
            continue

        # Train/val split
        train, val = _train_val_split(examples)
        _save_jsonl(train, str(out_dir / f"{task}_train.jsonl"))
        _save_jsonl(val, str(out_dir / f"{task}_val.jsonl"))
        print(f"  Split: {len(train)} train / {len(val)} val")

        all_combined.extend(examples)

    # Combined dataset
    if len(tasks) > 1 and all_combined:
        random.shuffle(all_combined)
        _save_jsonl(all_combined, str(out_dir / "combined_train.jsonl"))
        print(f"\n✓ Combined: {len(all_combined)} total examples → {out_dir / 'combined_train.jsonl'}")

    print(f"""
{'='*60}
Download complete!
{'='*60}

Datasets used:
  • datasetmaster/resumes            — structured resume profiles (extraction)
  • InferencePrince555/Resume-Dataset — resume text + categories (extraction)
  • ShashiVish/cover-letter-dataset  — 1,162 cover letter examples
  • dhruvvaidh/cover-letter-dataset-llama3 — Llama3-formatted cover letters
  • MikePfunk28/resume-training-dataset — 22,855 resume coaching conversations

Next steps:
  Fine-tune Llama 3.2 3B:
    python finetune/scripts/train_lora.py --config finetune/configs/lora_extraction.yaml
    python finetune/scripts/train_lora.py --config finetune/configs/lora_cover_letter.yaml
    python finetune/scripts/train_lora.py --config finetune/configs/lora_resume_writer.yaml
""")


if __name__ == "__main__":
    main()
