from fastapi import FastAPI

app = FastAPI(title="AutoApplyHub API")

@app.get("/")
async def root():
    return {"message": "Welcome to AutoApplyHub API"}

# TODO: Add endpoints for /parse_resume, /start_autoapply
