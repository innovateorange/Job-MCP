# Architecture Overview

## Components
- **Frontend**: Next.js for UI (profile, dashboard).
- **Backend**: FastAPI for APIs and MCP.
- **BaaS**: Supabase for DB, auth, storage.
- **MCP**: Celery worker for Claude parsing and Playwright automation.

## Flow
1. User uploads resume → Supabase Storage → FastAPI → Claude → Supabase DB.
2. Auto-apply: Celery task fetches jobs, matches via pgvector/LLM, submits via Playwright.
3. Dashboard: Realtime stats from Supabase.

## Notes
- Use RLS for privacy.
- Rate limit automation to comply with TOS.
