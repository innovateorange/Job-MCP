"""
Resume Processor — Job-MCP Project (LangChain Edition)
======================================================
Handles file I/O (PDF text extraction, image OCR) and delegates
intelligent parsing (skill extraction, profile structuring) to
LangChain chains.

The T5 model has been replaced by the configurable LLM pipeline.
Keyword matching is retained as a fast fallback / merge source inside
the skill_chain.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

from paddleocr import PaddleOCR
import PyPDF2

# Lazy-init OCR (heavy import)
_ocr: Optional[PaddleOCR] = None


def _get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        print("Initializing PaddleOCR...")
        _ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr


# ── Text extraction (unchanged) ────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extract text content from a PDF file."""
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                print(f"  - Extracted page {i}/{len(reader.pages)}")
    except FileNotFoundError:
        print(f"Error: File not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    return text


def extract_text_from_image(image_path: str) -> Optional[str]:
    """Extract text from an image using PaddleOCR."""
    try:
        ocr = _get_ocr()
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            print("Warning: No text detected in image")
            return ""
        text = " ".join(line[1][0] for line in result[0])
        print(f"  - Extracted {len(result[0])} text lines from image")
        return text
    except FileNotFoundError:
        print(f"Error: File not found at {image_path}")
        return None
    except Exception as e:
        print(f"Error processing image: {e}")
        return None


def clean_text(text: str) -> str:
    """Clean and normalise extracted text."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:()\-@#+/]", "", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",{2,}", ",", text)
    return text.strip()


def extract_contact_info(text: str) -> dict:
    """Extract email and phone from resume text."""
    info: dict = {}
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
    if emails:
        info["email"] = emails[0]
    phones = re.findall(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b", text)
    if phones:
        info["phone"] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
    return info


# ── Main processing pipeline ───────────────────────────────────────────

def extract_raw_text(file_path: str) -> Optional[str]:
    """
    Extract raw text from a resume file (PDF or image).
    Returns cleaned text or None on failure.
    """
    path = Path(file_path)
    if not path.exists():
        return None

    ext = path.suffix.lower()
    if ext == ".pdf":
        raw = extract_text_from_pdf(file_path)
    elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        raw = extract_text_from_image(file_path)
    else:
        return None

    if raw is None or len(raw.strip()) == 0:
        return None

    return clean_text(raw)


async def process_resume_full(file_path: str, llm=None) -> dict:
    """
    Full pipeline: extract text -> parse with LangChain chains.

    Parameters
    ----------
    file_path : str
        Path to the resume file (PDF or image).
    llm : BaseChatModel | None
        Override the default LLM provider.

    Returns
    -------
    dict with keys: file_name, file_type, full_text, profile, skills,
                    contact_info, processing_status
    """
    from backend.app.chains.resume_chain import build_resume_chain
    from backend.app.chains.skill_chain import build_skill_chain

    path = Path(file_path)

    # Step 1: Extract text
    cleaned_text = extract_raw_text(file_path)
    if cleaned_text is None:
        return {
            "error": "Failed to extract text or unsupported format",
            "file_path": file_path,
            "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"],
        }

    # Step 2: Run LangChain chains in parallel
    resume_chain = build_resume_chain(llm=llm)
    skill_chain = build_skill_chain(llm=llm)

    profile_result, skill_result = await asyncio.gather(
        resume_chain.ainvoke({"resume_text": cleaned_text}),
        skill_chain.ainvoke({"text": cleaned_text}),
    )

    # Step 3: Merge skill results into profile
    if isinstance(profile_result, dict):
        chain_skills = set(profile_result.get("skills", []))
        extra_skills = set(skill_result.get("skills", []))
        profile_result["skills"] = sorted(chain_skills | extra_skills, key=str.lower)

    # Step 4: Contact info (fast regex, no LLM needed)
    contact_info = extract_contact_info(cleaned_text)

    return {
        "file_name": path.name,
        "file_type": path.suffix.lower(),
        "full_text": cleaned_text,
        "text_length": len(cleaned_text),
        "profile": profile_result,
        "skills": skill_result,
        "contact_info": contact_info or None,
        "processing_status": "success",
    }


# ── CLI entrypoint (kept for standalone use) ───────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python resume_processor.py <path_to_resume>")
        sys.exit(1)

    result = asyncio.run(process_resume_full(sys.argv[1]))

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
