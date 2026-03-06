"""
Resume Writer Chain
===================
Given a candidate's current profile and a target job description,
rewrites / improves the resume to be tailored for that specific role.

Input:  {"profile": dict/str, "job_description": str}
Output: {
    "improved_resume": str,
    "changes_made": [str],
    "skills_highlighted": [str],
    "word_count": int
}
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.services.llm_provider import get_default_llm


class ResumeWriterOutput(BaseModel):
    improved_resume: str = Field(description="The full improved resume text with sections")
    changes_made: list[str] = Field(
        default_factory=list,
        description="List of specific improvements made",
    )
    skills_highlighted: list[str] = Field(
        default_factory=list,
        description="Skills from the profile that were emphasized for this role",
    )
    word_count: int = Field(description="Approximate word count of the improved resume")


_SYSTEM = """\
You are an expert resume writer for CS students and developers.

Given the candidate's current profile and a target job description,
rewrite their resume to be tailored for that specific role.

Return a JSON object matching this schema — nothing else:
{format_instructions}

Guidelines:
- Reorder and reword experience bullets to emphasize relevant skills
  and achievements for the target role.
- Add a tailored professional summary / objective at the top.
- Use strong action verbs and quantified achievements where possible
  (e.g. "Reduced API latency by 40%" instead of "Improved performance").
- Format the resume with clear sections: Summary, Education, Experience,
  Projects, Skills, Certifications.
- Keep ALL truthful information from the original profile — do NOT
  fabricate experience, companies, or skills.
- Target length: 400-600 words.
- If the candidate is a poor fit, still produce the best possible resume
  but note gaps in changes_made.
"""

_HUMAN = """\
Current profile:
```json
{profile}
```

Target job description:
\"\"\"
{job_description}
\"\"\"
"""


def build_resume_writer_chain(llm: BaseChatModel | None = None):
    """
    Build chain:  (profile, job_description) → ResumeWriterOutput
    """
    llm = llm or get_default_llm()
    parser = JsonOutputParser(pydantic_object=ResumeWriterOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return chain
