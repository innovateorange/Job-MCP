"""
Apply Router — /apply/*
=======================
Endpoints that trigger background auto-apply jobs via Celery.
The actual browser automation is handled by the LangChain apply agent.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.tasks.celery_app import celery_app

router = APIRouter(prefix="/apply", tags=["apply"])


class AutoApplyRequest(BaseModel):
    user_id: str
    job_urls: list[str]
    credentials: dict  # {"email": "...", "password": "..."}
    preferences: dict = {}
    resume_path: str = ""
    provider: Optional[str] = None  # LLM provider override


class AutoApplyResponse(BaseModel):
    task_id: str
    status: str
    message: str
    jobs_queued: int


@router.post("/start", response_model=AutoApplyResponse)
async def start_autoapply(req: AutoApplyRequest):
    """
    Queue auto-apply tasks for one or more job URLs.

    Each job URL becomes a separate Celery task so they can run
    in parallel across workers.
    """
    if not req.job_urls:
        raise HTTPException(status_code=400, detail="No job URLs provided")

    task_ids = []
    for url in req.job_urls:
        task = celery_app.send_task(
            "backend.tasks.celery_app.apply_to_job",
            kwargs={
                "user_id": req.user_id,
                "job_url": url,
                "credentials": req.credentials,
                "preferences": req.preferences,
                "resume_path": req.resume_path,
                "provider": req.provider,
            },
        )
        task_ids.append(task.id)

    return AutoApplyResponse(
        task_id=task_ids[0] if len(task_ids) == 1 else ",".join(task_ids),
        status="queued",
        message=f"Queued {len(req.job_urls)} application(s)",
        jobs_queued=len(req.job_urls),
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of an auto-apply task."""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.post("/stop/{task_id}")
async def stop_task(task_id: str):
    """Revoke / cancel a running auto-apply task."""
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "status": "revoked"}
