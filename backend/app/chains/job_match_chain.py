"""
Job Matching Chain
==================
Scores how well a candidate profile matches a job description and provides
actionable feedback.

Input:  {"profile": dict, "job_description": str}
Output: {
    "score": float (0-100),
    "matching_skills": [...],
    "missing_skills": [...],
    "recommendation": str,
    "fit_level": "strong" | "moderate" | "weak"
}
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.services.llm_provider import get_default_llm


class JobMatchResult(BaseModel):
    score: float = Field(description="Match score 0-100")
    fit_level: str = Field(description="'strong' (70+), 'moderate' (40-69), or 'weak' (<40)")
    matching_skills: list[str] = Field(default_factory=list, description="Skills the candidate has that the job wants")
    missing_skills: list[str] = Field(default_factory=list, description="Skills the job wants that the candidate lacks")
    recommendation: str = Field(description="Brief recommendation on whether to apply and how to improve chances")
    key_strengths: list[str] = Field(default_factory=list, description="Top strengths relative to this role")


_SYSTEM = """\
You are a career-matching AI for a job application platform.

Given a candidate profile (JSON) and a job description, evaluate how well
the candidate fits the role.

Return a JSON object matching this schema — nothing else:
{format_instructions}

Scoring guidelines:
- 80-100: Exceeds requirements, strong match
- 60-79:  Meets most requirements
- 40-59:  Partial match, some gaps
- 20-39:  Significant gaps
- 0-19:   Poor fit

Be honest but constructive.  Focus on actionable feedback.
"""

_HUMAN = """\
Candidate profile:
```json
{profile}
```

Job description:
\"\"\"
{job_description}
\"\"\"
"""


def build_job_match_chain(llm: BaseChatModel | None = None):
    """
    Build chain:  (profile, job_description) → JobMatchResult

    Input dict keys: "profile" (JSON string or dict), "job_description" (str)
    """
    llm = llm or get_default_llm()
    parser = JsonOutputParser(pydantic_object=JobMatchResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return chain
