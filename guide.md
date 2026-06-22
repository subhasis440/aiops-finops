# AI Cloud Cost Detective - Guide

## Why this file exists

This guide is the handoff document for any new AI model or developer joining the conversation.
Read this first to avoid rediscovery work.

## Project objective

Build a full-stack application that:

1. Authenticates users with custom JWT auth.
2. Scans cloud resources (Azure first, AWS and GCP supported by scanner abstraction).
3. Runs AI-based cost analysis using OpenAI.
4. Streams live progress using WebSocket.
5. Stores analysis history in PostgreSQL.
6. Displays dashboard, report, and history in React.

## Current implementation status

Implemented in this repository:

1. Backend (FastAPI):
   - Auth endpoints: signup and login.
   - Protected endpoints: providers, scopes, resource-groups, analyze, history, analysis by id.
   - WebSocket endpoint for progress updates by analysis id.
   - Background analysis workflow with status updates.
2. Cloud scanner abstraction:
   - Base scanner interface.
   - Azure scanner with CLI checks and normalized resource output.
   - AWS and GCP scanner implementations using respective CLIs.
3. AI analysis:
   - OpenAI chat completions integration with strict JSON normalization.
4. Database:
   - asyncpg pool setup.
   - users and analyses tables with initialization on startup.
   - CRUD helpers for auth and analysis history.
5. Frontend (Vite + React + TypeScript + Tailwind):
   - Login, Signup, Dashboard, Report, History pages.
   - Auth context with token persistence.
   - API client with Bearer token interceptor.
   - WebSocket progress tracker component.

## Key files to know first

1. backend/main.py
2. backend/auth.py
3. backend/db.py
4. backend/ai_analyzer.py
5. backend/scanner_factory.py
6. backend/scanners/
7. frontend/src/App.tsx
8. frontend/src/auth.tsx
9. frontend/src/api.ts
10. frontend/src/pages/
11. plan.md
12. README.md

## Environment variables

Backend .env values:

1. OPENAI_API_KEY
2. DATABASE_URL
3. JWT_SECRET
4. JWT_EXP_HOURS (default 24)

Frontend optional .env values:

1. VITE_API_BASE_URL (defaults to http://localhost:8000)

## Local setup and run

### 1) Backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload
```

### 2) Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

### 3) Build validation

```powershell
Set-Location frontend
npm run build
```

## Required external dependencies

1. Azure CLI installed and authenticated for Azure scans.
2. AWS CLI authenticated for AWS scans.
3. gcloud CLI authenticated for GCP scans.
4. PostgreSQL reachable from DATABASE_URL.
5. OpenAI API key present.

## API behavior summary

Public endpoints:

1. GET /api/health
2. POST /api/auth/signup
3. POST /api/auth/login

Protected endpoints (Authorization: Bearer token):

1. GET /api/providers
2. GET /api/scopes?provider=azure|aws|gcp
3. GET /api/resource-groups
4. POST /api/analyze
5. GET /api/history
6. GET /api/analyses/{analysis_id}

WebSocket:

1. /ws/progress/{analysis_id}?token=<jwt>

## Known operational notes

1. In this environment, ripgrep is not installed. Use PowerShell Get-ChildItem and Select-String.
2. Frontend build is already validated successfully.
3. Backend source compiles successfully with compileall.
4. End-to-end runtime still depends on valid .env secrets and live cloud credentials.

## How to continue with a new AI model

Use this startup checklist in the first prompt:

1. Read guide.md, changelog.md, plan.md.
2. Confirm environment variables and runtime prerequisites.
3. Run backend and frontend.
4. Run end-to-end smoke test: signup -> login -> scope select -> run analysis -> progress -> report -> history.
5. Record all new changes in changelog.md.

## Change discipline

Whenever code changes are made:

1. Update changelog.md with date, area, and impact.
2. If architecture or setup changed, update this guide.
3. Keep entries short, factual, and ordered.
