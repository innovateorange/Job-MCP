"""
Cover Letter Generation Chain
==============================
Generates a tailored cover letter given a candidate profile and job
description.

Input:  {"profile": dict/str, "job_description": str, "company_name": str, "tone": str}
Output: {"cover_letter": str, "word_count": int}
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.app.services.llm_provider import get_default_llm


class CoverLetterOutput(BaseModel):
    cover_letter: str = Field(description="The full cover letter text")
    word_count: int = Field(description="Approximate word count")
    key_points: list[str] = Field(
        default_factory=list,
        description="Main selling points highlighted in the letter",
    )


_SYSTEM = """\
You are a professional cover-letter writer for CS students and early-career
developers.

Given the candidate's profile and a target job description, write a concise,
compelling cover letter.

Return a JSON object matching this schema — nothing else:
{format_instructions}

Guidelines:
- Tone: {tone} (default: professional but personable)
- Length: 250-400 words
- Highlight the candidate's most relevant skills and experience
- Mention the company by name
- Avoid generic filler; be specific
- Do NOT fabricate experience or skills not present in the profile
"""

_HUMAN = """\
Candidate profile:
```json
{profile}
```

Company: {company_name}

Job description:
\"\"\"
{job_description}
\"\"\"
"""


def build_cover_letter_chain(llm: BaseChatModel | None = None):
    """
    Build chain:  (profile, job_description, company_name, tone) → CoverLetterOutput
    """
    llm = llm or get_default_llm()
    parser = JsonOutputParser(pydantic_object=CoverLetterOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("human", _HUMAN),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return chain
