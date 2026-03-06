"""
Resume Parsing Chain
====================
Takes raw resume text (from OCR / PyPDF2) and produces a structured JSON
profile using an LLM.  Works with *any* provider registered in llm_provider.

Returns
-------
dict with keys: name, email, phone, summary, education, experience, skills,
                certifications, projects, languages
"""

from __future__ import annotations

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from backend.app.services.llm_provider import get_default_llm


# ── Output schema (doubles as documentation for the LLM) ───────────────

class Education(BaseModel):
    institution: str = Field(description="School or university name")
    degree: str = Field(description="Degree obtained or pursuing")
    field: str = Field(default="", description="Major / field of study")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date or 'Present'")
    gpa: str = Field(default="", description="GPA if listed")


class Experience(BaseModel):
    company: str = Field(description="Company or organization name")
    title: str = Field(description="Job title")
    start_date: str = Field(default="", description="Start date")
    end_date: str = Field(default="", description="End date or 'Present'")
    description: str = Field(default="", description="Role description / bullets")
    location: str = Field(default="", description="Location if listed")


class Project(BaseModel):
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Brief description")
    technologies: list[str] = Field(default_factory=list, description="Tech used")
    url: str = Field(default="", description="Link if provided")


class ResumeProfile(BaseModel):
    name: str = Field(default="", description="Candidate full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="Location / address")
    summary: str = Field(default="", description="Professional summary")
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="All skills detected")
    certifications: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list, description="Spoken languages")
    links: list[str] = Field(default_factory=list, description="LinkedIn, GitHub, etc.")


# ── Prompt ──────────────────────────────────────────────────────────────

_SYSTEM = """\
You are an expert resume parser for a job-application platform.

Given the raw text extracted from a candidate's resume, produce a single
JSON object that conforms **exactly** to the schema below.  Do NOT include
any text outside the JSON block.

{format_instructions}

Rules:
- Extract every piece of information you can find; leave fields as empty
  strings or empty lists when the information is not present.
- Normalise skill names (e.g. "JS" → "JavaScript", "ML" → "Machine Learning").
- Dates should use the format found in the resume (e.g. "Jan 2023", "2023").
- Preserve the original meaning; do not invent information.
"""

_HUMAN = """\
Resume text:
\"\"\"
{resume_text}
\"\"\"
"""


# ── Chain builder ───────────────────────────────────────────────────────

def build_resume_chain(llm: BaseChatModel | None = None):
    """
    Build an LCEL chain:  resume_text → ResumeProfile (dict).

    Parameters
    ----------
    llm : BaseChatModel | None
        Override the default LLM.  Pass ``None`` to use the configured
        default from ``LLM_PROVIDER`` env var.
    """
    llm = llm or get_default_llm()
    parser = JsonOutputParser(pydantic_object=ResumeProfile)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return chain
