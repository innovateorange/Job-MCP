"""
LangChain Chains — Job-MCP Pipeline
====================================
Each module exposes one or more LCEL chains that compose the full pipeline:

  resume_chain        – parse raw resume text → structured profile JSON
  skill_chain         – extract / normalize skills from text
  job_match_chain     – score candidate–job fit
  cover_letter_chain  – generate tailored cover letters
  resume_writer_chain – rewrite a resume tailored to a job description
"""

from backend.app.chains.resume_chain import build_resume_chain
from backend.app.chains.skill_chain import build_skill_chain
from backend.app.chains.job_match_chain import build_job_match_chain
from backend.app.chains.cover_letter_chain import build_cover_letter_chain
from backend.app.chains.resume_writer_chain import build_resume_writer_chain

__all__ = [
    "build_resume_chain",
    "build_skill_chain",
    "build_job_match_chain",
    "build_cover_letter_chain",
    "build_resume_writer_chain",
]
