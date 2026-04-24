"""
Auto-Apply Agent
================
A LangChain agent that orchestrates browser-based job applications using
Playwright as a tool.  The agent decides *how* to fill forms, which fields
to populate, and when to submit — all driven by the LLM.

This replaces the old imperative Playwright script with an agent loop that
can adapt to different job-site layouts.

Usage
-----
    agent = build_apply_agent()
    result = await agent.ainvoke({
        "profile": {...},
        "job_url": "https://...",
        "credentials": {"email": "...", "password": "..."},
        "preferences": {"job_types": ["full-time"], ...},
    })
"""

from __future__ import annotations

import json
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent

from backend.app.services.llm_provider import get_default_llm


# ── Playwright browser tools (wrapped for LangChain) ───────────────────

@tool
async def navigate_to_url(url: str) -> str:
    """Navigate the browser to the given URL.  Returns the page title."""
    from backend.app.services.browser import get_page
    page = await get_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    return f"Navigated to: {await page.title()}"


@tool
async def get_page_text() -> str:
    """Return visible text content of the current page (truncated to 4000 chars)."""
    from backend.app.services.browser import get_page
    page = await get_page()
    text = await page.inner_text("body")
    return text[:4000]


@tool
async def get_form_fields() -> str:
    """List all visible form inputs on the current page with their labels, names, types, and current values."""
    from backend.app.services.browser import get_page
    page = await get_page()
    fields = await page.evaluate("""() => {
        const inputs = document.querySelectorAll('input, select, textarea');
        return Array.from(inputs)
            .filter(el => el.offsetParent !== null)  // visible only
            .map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                label: el.labels?.[0]?.textContent?.trim() || '',
                value: el.value || '',
                options: el.tagName === 'SELECT'
                    ? Array.from(el.options).map(o => o.text)
                    : undefined
            }));
    }""")
    return json.dumps(fields, indent=2)


@tool
async def fill_field(selector: str, value: str) -> str:
    """Fill a form field identified by CSS selector with the given value."""
    from backend.app.services.browser import get_page
    page = await get_page()
    await page.fill(selector, value)
    return f"Filled '{selector}' with '{value}'"


@tool
async def select_option(selector: str, value: str) -> str:
    """Select a dropdown option by visible text."""
    from backend.app.services.browser import get_page
    page = await get_page()
    await page.select_option(selector, label=value)
    return f"Selected '{value}' in '{selector}'"


@tool
async def click_element(selector: str) -> str:
    """Click an element by CSS selector."""
    from backend.app.services.browser import get_page
    page = await get_page()
    await page.click(selector)
    return f"Clicked '{selector}'"


@tool
async def upload_file(selector: str, file_path: str) -> str:
    """Upload a file to a file-input element."""
    from backend.app.services.browser import get_page
    page = await get_page()
    await page.set_input_files(selector, file_path)
    return f"Uploaded '{file_path}' to '{selector}'"


@tool
async def take_screenshot() -> str:
    """Take a screenshot and save it.  Returns the file path."""
    import uuid
    from backend.app.services.browser import get_page
    page = await get_page()
    path = f"/tmp/screenshot_{uuid.uuid4().hex[:8]}.png"
    await page.screenshot(path=path)
    return f"Screenshot saved to {path}"


@tool
async def wait_for_selector(selector: str, timeout_ms: int = 5000) -> str:
    """Wait for an element to appear on the page."""
    from backend.app.services.browser import get_page
    page = await get_page()
    try:
        await page.wait_for_selector(selector, timeout=timeout_ms)
        return f"Element '{selector}' found"
    except Exception:
        return f"Element '{selector}' not found within {timeout_ms}ms"


_TOOLS = [
    navigate_to_url,
    get_page_text,
    get_form_fields,
    fill_field,
    select_option,
    click_element,
    upload_file,
    take_screenshot,
    wait_for_selector,
]


# ── Agent prompt ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an automated job-application agent.  Your goal is to navigate to a
job posting URL and submit a complete application on behalf of the candidate.

Candidate profile:
```json
{profile}
```

Credentials (for login if needed):
```json
{credentials}
```

Preferences:
```json
{preferences}
```

Resume file path: {resume_path}

Instructions:
1. Navigate to the job URL.
2. If a login is required, log in using the provided credentials.
3. Inspect form fields on the page.
4. Fill in all required fields using the candidate's profile data.
5. Upload the resume if a file-upload field is present.
6. Review the form, then submit.
7. Take a screenshot of the confirmation page.
8. Report the outcome: success, failure, or needs-human-review.

Rules:
- NEVER fabricate information not in the profile.
- If a required field cannot be filled from the profile, report
  "needs-human-review" with the field name.
- Be respectful of rate limits — do not spam.
- If CAPTCHA is detected, report "needs-human-review".
"""


# ── Agent builder ───────────────────────────────────────────────────────

def build_apply_agent(llm: BaseChatModel | None = None) -> AgentExecutor:
    """
    Build a LangChain tool-calling agent for auto-apply.

    The agent uses Playwright browser tools to navigate job sites,
    fill forms, and submit applications.
    """
    llm = llm or get_default_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "Apply to this job: {job_url}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, _TOOLS, prompt)

    return AgentExecutor(
        agent=agent,
        tools=_TOOLS,
        verbose=True,
        max_iterations=25,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )
