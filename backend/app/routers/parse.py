"""
Parse Router — /parse/*
=======================
Endpoints for resume parsing, skill extraction, and job matching.
All LLM work is delegated to LangChain chains via llm_provider.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.services.llm_provider import get_llm
from backend.app.services.model_loader import load_task_model
from backend.app.services.resume_processor import process_resume_full
from backend.app.chains.skill_chain import build_skill_chain
from backend.app.chains.job_match_chain import build_job_match_chain
from backend.app.chains.cover_letter_chain import build_cover_letter_chain
from backend.app.chains.resume_writer_chain import build_resume_writer_chain

router = APIRouter(prefix="/parse", tags=["parse"])


def _resolve_llm(provider: Optional[str] = None, task: Optional[str] = None):
    """Build an LLM from the optional provider override, else try task-specific
    fine-tuned model, else use default."""
    if provider:
        return get_llm(provider=provider)
    if task:
        try:
            return load_task_model(task=task)
        except Exception:
            pass  # fall through to default
    return None  # chains will use get_default_llm()


# ── Resume parsing ──────────────────────────────────────────────────────

@router.post("/resume")
async def parse_resume(
    file: UploadFile = File(...),
    provider: Optional[str] = Form(None),
):
    """
    Upload a resume (PDF or image) and get a structured profile + skills.

    Query params:
      provider  – override LLM provider ("anthropic", "openai", etc.)
    """
    # Save uploaded file to temp location
    suffix = os.path.splitext(file.filename or "resume.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        llm = _resolve_llm(provider, task="extraction")
        result = await process_resume_full(tmp_path, llm=llm)

        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])

        return result
    finally:
        os.unlink(tmp_path)


# ── Skill extraction (standalone) ──────────────────────────────────────

class SkillRequest(BaseModel):
    text: str
    provider: Optional[str] = None


@router.post("/skills")
async def extract_skills(req: SkillRequest):
    """Extract and categorise skills from arbitrary text."""
    llm = _resolve_llm(req.provider, task="extraction")
    chain = build_skill_chain(llm=llm)
    result = await chain.ainvoke({"text": req.text})
    return result


# ── Job matching ────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    profile: dict
    job_description: str
    provider: Optional[str] = None


@router.post("/match")
async def match_job(req: MatchRequest):
    """Score how well a candidate profile matches a job description."""
    llm = _resolve_llm(req.provider, task="extraction")
    chain = build_job_match_chain(llm=llm)
    result = await chain.ainvoke({
        "profile": json.dumps(req.profile),
        "job_description": req.job_description,
    })
    return result


# ── Cover letter generation ─────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    profile: dict
    job_description: str
    company_name: str = "the company"
    tone: str = "professional but personable"
    provider: Optional[str] = None


@router.post("/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest):
    """Generate a tailored cover letter."""
    llm = _resolve_llm(req.provider, task="cover_letter")
    chain = build_cover_letter_chain(llm=llm)
    result = await chain.ainvoke({
        "profile": json.dumps(req.profile),
        "job_description": req.job_description,
        "company_name": req.company_name,
        "tone": req.tone,
    })
    return result


# ── Resume writing / improvement ───────────────────────────────────────

class ResumeWriterRequest(BaseModel):
    profile: dict
    job_description: str
    provider: Optional[str] = None


@router.post("/improve-resume")
async def improve_resume(req: ResumeWriterRequest):
    """Rewrite / improve a resume tailored for a target job description."""
    llm = _resolve_llm(req.provider, task="resume_writer")
    chain = build_resume_writer_chain(llm=llm)
    result = await chain.ainvoke({
        "profile": json.dumps(req.profile),
        "job_description": req.job_description,
    })
    return result
