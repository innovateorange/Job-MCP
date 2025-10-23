from fastapi import APIRouter

router = APIRouter(prefix="/parse", tags=["parse"])

@router.post("/resume")
async def parse_resume():
    # TODO: Extract text from PDF, call Claude API, store in Supabase
    return {"status": "Not implemented"}
