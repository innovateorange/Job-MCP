from fastapi import FastAPI

app = FastAPI(title="Job-MCP API")

@app.get("/")
async def root():
    return {"message": "Welcome to Job-MCP API"}

# TODO: Add endpoints for /parse_resume, /start_autoapply
