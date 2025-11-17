# Vercel entrypoint - imports the FastAPI app from backend
from backend.app.main import app

__all__ = ["app"]

