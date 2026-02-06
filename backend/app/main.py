from fastapi import FastAPI
from backend.app.routers import parse, apply

app = FastAPI(title="Job-MCP API")

app.include_router(parse.router)
app.include_router(apply.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Job-MCP API"}
