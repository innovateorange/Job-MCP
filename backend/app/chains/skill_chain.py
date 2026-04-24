"""
Skill Extraction Chain
======================
Extracts, normalises, and categorises skills from arbitrary text (resume,
job description, or freeform input).  Combines keyword matching (fast,
deterministic) with LLM extraction (catches non-obvious skills).

The chain returns a dict:
  {
    "skills": ["Python", "React", ...],
    "categorized": {
      "programming_languages": [...],
      "frameworks": [...],
      "databases": [...],
      "cloud_devops": [...],
      "data_ml": [...],
      "tools": [...],
      "soft_skills": [...],
      "other": [...]
    }
  }
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from pydantic import BaseModel, Field

from backend.app.services.llm_provider import get_default_llm


# ── Keyword catalogue (deterministic, zero-latency) ────────────────────

_SKILL_KEYWORDS: list[str] = [
    # Programming
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby",
    "php", "swift", "kotlin", "go", "rust", "scala", "r", "matlab",
    # Web
    "html", "css", "react", "angular", "vue", "next.js", "nuxt",
    "node.js", "express", "django", "flask", "fastapi", "spring",
    "asp.net", "tailwind", "sass", "webpack", "vite",
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "oracle",
    "sqlite", "dynamodb", "cassandra", "neo4j", "supabase", "firebase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins",
    "terraform", "ansible", "ci/cd", "github actions", "gitlab",
    # Data / ML
    "machine learning", "deep learning", "data analysis", "data science",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "langchain", "llm", "nlp", "computer vision", "spark", "hadoop",
    # Tools
    "git", "jira", "figma", "postman", "swagger",
    # Soft
    "leadership", "communication", "teamwork", "problem solving",
    "project management", "agile", "scrum",
]


def _keyword_extract(text: str) -> list[str]:
    """Fast deterministic skill extraction via regex word-boundary matching."""
    text_lower = text.lower()
    found = []
    for skill in _SKILL_KEYWORDS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


# ── LLM-based extraction schema ────────────────────────────────────────

class CategorizedSkills(BaseModel):
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_devops: list[str] = Field(default_factory=list)
    data_ml: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class SkillOutput(BaseModel):
    skills: list[str] = Field(description="Flat deduplicated skill list")
    categorized: CategorizedSkills = Field(description="Skills grouped by category")


_SYSTEM = """\
You are a technical recruiter AI.  Given the following text, extract every
skill, technology, tool, framework, and soft skill mentioned.

Return a JSON object matching this schema — nothing else:
{format_instructions}

Rules:
- Normalise names (e.g. "JS" → "JavaScript").
- Deduplicate.
- If unsure whether something is a skill, include it under "other".
"""

_HUMAN = "Text:\n\"\"\"\n{text}\n\"\"\""


# ── Chain builder ───────────────────────────────────────────────────────

def build_skill_chain(llm: BaseChatModel | None = None):
    """
    Build a chain that merges keyword + LLM skill extraction.

    Input:  {"text": str}
    Output: {"skills": [...], "categorized": {...}}
    """
    llm = llm or get_default_llm()
    parser = JsonOutputParser(pydantic_object=SkillOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ]).partial(format_instructions=parser.get_format_instructions())

    llm_branch = prompt | llm | parser
    keyword_branch = RunnableLambda(lambda inp: _keyword_extract(inp["text"]))

    parallel = RunnableParallel(llm_result=llm_branch, keyword_result=keyword_branch)

    def _merge(results: dict[str, Any]) -> dict:
        llm_skills: list[str] = results["llm_result"].get("skills", [])
        kw_skills: list[str] = results["keyword_result"]
        # Merge & deduplicate (case-insensitive)
        seen: set[str] = set()
        merged: list[str] = []
        for s in llm_skills + kw_skills:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(s.strip())
        categorized = results["llm_result"].get("categorized", {})
        return {"skills": sorted(merged, key=str.lower), "categorized": categorized}

    chain = parallel | RunnableLambda(_merge)
    return chain
