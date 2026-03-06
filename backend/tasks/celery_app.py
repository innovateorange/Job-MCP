"""
Celery App & Tasks — Job-MCP
=============================
Defines the Celery worker and all background tasks.
The auto-apply task uses the LangChain agent from chains/apply_agent.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from celery import Celery

# ── Celery configuration ───────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "job_mcp_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # one task at a time (browser-heavy)
    task_soft_time_limit=300,      # 5 min soft limit
    task_time_limit=360,           # 6 min hard limit
)


# ── Helper to run async code inside Celery (sync) workers ──────────────

def _run_async(coro):
    """Run an async coroutine in a new event loop (Celery tasks are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="backend.tasks.celery_app.apply_to_job", bind=True)
def apply_to_job(
    self,
    user_id: str,
    job_url: str,
    credentials: dict,
    preferences: dict,
    resume_path: str = "",
    provider: Optional[str] = None,
) -> dict:
    """
    Apply to a single job using the LangChain auto-apply agent.

    This task:
      1. Builds the agent with the requested (or default) LLM provider
      2. Invokes the agent with the job URL and candidate data
      3. Cleans up the browser
      4. Returns the outcome
    """
    from backend.app.chains.apply_agent import build_apply_agent
    from backend.app.services.llm_provider import get_llm
    from backend.app.services.browser import close_browser

    self.update_state(state="RUNNING", meta={"job_url": job_url})

    try:
        llm = get_llm(provider=provider) if provider else None
        agent = build_apply_agent(llm=llm)

        result = _run_async(agent.ainvoke({
            "profile": json.dumps(preferences.get("profile", {})),
            "job_url": job_url,
            "credentials": json.dumps(credentials),
            "preferences": json.dumps(preferences),
            "resume_path": resume_path or "N/A",
        }))

        output = result.get("output", "")
        return {
            "job_url": job_url,
            "status": "success",
            "agent_output": output,
            "steps": len(result.get("intermediate_steps", [])),
        }

    except Exception as e:
        return {
            "job_url": job_url,
            "status": "failed",
            "error": str(e),
        }
    finally:
        _run_async(close_browser())


@celery_app.task(name="backend.tasks.celery_app.parse_resume_async")
def parse_resume_async(
    file_path: str,
    user_id: str,
    provider: Optional[str] = None,
) -> dict:
    """
    Background resume parsing task.
    Useful for large files where the user doesn't want to wait on the
    HTTP request.
    """
    from backend.app.services.resume_processor import process_resume_full
    from backend.app.services.llm_provider import get_llm

    llm = get_llm(provider=provider) if provider else None
    result = _run_async(process_resume_full(file_path, llm=llm))
    # TODO: Store result in Supabase under user_id
    return result
