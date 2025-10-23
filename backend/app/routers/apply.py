from fastapi import APIRouter

router = APIRouter(prefix="/apply", tags=["apply"])

@router.post("/start")
async def start_autoapply():
    # TODO: Trigger Celery task for Playwright automation
    return {"status": "Not implemented"}
