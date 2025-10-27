# Job-MCP

## Overview
Job-MCP is a web application for CS students to streamline job applications. Users create profiles, upload resumes, track application stats (e.g., applications sent, responses, success rates), and manage preferences. An AI-powered MCP (Model Completion Provider) parses resume/profile data using Claude API and automates job applications via browser automation on supported sites (e.g., LinkedIn, Indeed). The website is for setup and management, with the MCP handling background tasks.

This project prioritizes ethical automation: complies with site TOS where possible, requires user consent, and includes rate limits.

## Features
- **Profile Creation**: Upload resume, input preferences (e.g., job types).
- **Resume Parsing**: AI extracts structured data (skills, experience).
- **Job Tracking**: Dashboard for stats and history.
- **Auto-Apply MCP**: Matches jobs and submits applications.
- **Management**: View/edit applications, pause automation, notifications.

## Tech Stack
- **Frontend**: Next.js 14 (TypeScript), Tailwind CSS, shadcn/ui
- **Backend/API**: FastAPI (Python)
- **BaaS**: Supabase (PostgreSQL, pgvector, Auth, Storage)
- **AI/LLM**: Claude API with LangChain
- **Automation**: Playwright
- **Task Queue**: Celery + Redis
- **Deployment**: Vercel (Frontend), Render/Railway (Backend), Supabase

## Prerequisites
- **Node.js** >= 18 (for Next.js frontend)
- **Python** >= 3.10 (for FastAPI backend)
- **Redis** (for Celery task queue)
- **Git**
- **Accounts**: 
  - Supabase (database, auth, storage)
  - Anthropic (Claude API key)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/innovateorange/Job-MCP.git
cd Job-MCP
```

### 2. Frontend Setup
```bash
cd frontend
npm install
# Create .env.local with your Supabase credentials:
# NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
# NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
npm run dev  # Runs on http://localhost:3000
```

### 3. Backend Setup
```bash
# From project root
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Create .env file in backend/ with:
# ANTHROPIC_API_KEY=your_api_key
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key
# REDIS_URL=redis://localhost:6379

cd backend
uvicorn app.main:app --reload  # Runs on http://localhost:8000
```
4. **Celery Worker** (for MCP):
   ```
   celery -A tasks worker --loglevel=info
   ```
5. **Supabase Setup**:
   - Create a project.
   - Set up tables: `users`, `profiles`, `applications`, `preferences`.
   - Enable pgvector.
   - Configure RLS.
6. **Deployment**:
   - Frontend: Vercel (connect GitHub).
   - Backend: Render/Railway with Docker.
   - Set environment variables.

## Usage
- Sign up/login via Supabase Auth.
- Upload resume → MCP parses and populates profile.
- Set preferences → Start auto-apply.
- View dashboard for stats.

## Contributing
Fork, branch, submit PRs. Use conventional commits.

## License
MIT License. See LICENSE file.
