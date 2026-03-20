"""
Apply Router — /apply/*
=======================
Endpoints that trigger background auto-apply jobs via Celery.
The actual browser automation is handled by the LangChain apply agent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.tasks.celery_app import celery_app
from backend.app.services.supabase_client import get_supabase_client

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


class JobApplicationItem(BaseModel):
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str | None = None
    source: str | None = None
    auto_applied_at: datetime | None = None
    requires_follow_up: bool = False
    follow_up_confirmed: bool = False
    status: Literal["auto_applied", "follow_up_required", "completed"] = "auto_applied"
    metadata: dict[str, Any] = Field(default_factory=dict)


class StartAutoApplyInsertRequest(BaseModel):
    user_id: UUID
    jobs: list[JobApplicationItem]


class FollowUpUpdateRequest(BaseModel):
    follow_up_confirmed: bool


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


@router.post("/start-db")
async def start_autoapply_db(payload: StartAutoApplyInsertRequest):
    """Insert auto-apply results into Supabase for dashboard rendering."""
    if not payload.jobs:
        return {"status": "ok", "inserted": 0, "message": "No jobs in payload."}

    rows = []
    for job in payload.jobs:
        status = job.status
        if job.requires_follow_up and not job.follow_up_confirmed and status == "auto_applied":
            status = "follow_up_required"
        if job.follow_up_confirmed:
            status = "completed"

        rows.append(
            {
                "user_id": str(payload.user_id),
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "source": job.source,
                "auto_applied_at": (job.auto_applied_at or datetime.utcnow()).isoformat(),
                "requires_follow_up": job.requires_follow_up,
                "follow_up_confirmed": job.follow_up_confirmed,
                "status": status,
                "metadata": job.metadata,
            }
        )

    try:
        supabase = get_supabase_client()
        response = supabase.table("job_applications").insert(rows).execute()
        inserted = len(response.data or [])
        return {"status": "ok", "inserted": inserted, "rows": response.data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to insert job applications: {exc}") from exc


@router.get("/jobs/{user_id}")
async def list_jobs(user_id: UUID):
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("job_applications")
            .select("id, user_id, company, title, location, source, auto_applied_at, requires_follow_up, follow_up_confirmed, status, metadata, created_at, updated_at")
            .eq("user_id", str(user_id))
            .order("auto_applied_at", desc=True)
            .execute()
        )
        return {"status": "ok", "rows": response.data or []}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job applications: {exc}") from exc


@router.patch("/jobs/{job_id}/follow-up")
async def update_follow_up(job_id: UUID, payload: FollowUpUpdateRequest):
    next_status = "completed" if payload.follow_up_confirmed else "follow_up_required"

    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("job_applications")
            .update({"follow_up_confirmed": payload.follow_up_confirmed, "status": next_status})
            .eq("id", str(job_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Job application not found")

        return {"status": "ok", "row": response.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update follow-up: {exc}") from exc

