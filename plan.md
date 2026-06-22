# AI Cloud Cost Detective — Build Plan

## Overview

A full-stack AI-powered tool that scans cloud resources (Azure, AWS, GCP), detects cost issues via OpenAI, streams live progress over WebSocket, and persists analysis history in PostgreSQL with custom JWT auth.

**Scope:** Local dev only (cloud providers + OpenAI referenced via env vars).  
**Backend:** Flat structure with a `scanners/` abstraction for multi-cloud.  
**DB driver:** asyncpg (async — fits FastAPI).  
**Analysis flow:** `POST /api/analyze` returns `{analysis_id}` (HTTP 202) immediately; analysis runs in `BackgroundTasks`; progress is pushed over WebSocket keyed by `analysis_id`.

---

## Final Project Structure

```
backend/
├── main.py                  # FastAPI app, all endpoints, lifespan, WS, BackgroundTasks
├── auth.py                  # signup, login, get_current_user (JWT dependency)
├── db.py                    # asyncpg pool, init_db(), insert/query helpers
├── ai_analyzer.py           # OpenAI cost analysis (provider-agnostic)
├── scanner_factory.py       # get_scanner(provider) → CloudScanner
├── scanners/
│   ├── base.py              # Abstract CloudScanner interface
│   ├── azure.py             # az CLI → list_scopes(), list_resources(scope)
│   ├── aws.py               # aws CLI → list_scopes(), list_resources(scope)
│   └── gcp.py               # gcloud CLI → list_scopes(), list_resources(scope)
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── App.tsx              # Routes + protected-route wrapper
│   ├── main.tsx
│   ├── auth.tsx             # AuthProvider context
│   ├── api.ts               # Axios instance + Bearer interceptor
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Signup.tsx
│   │   ├── Dashboard.tsx    # Cloud selector + scope dropdown + Run Analysis
│   │   ├── Report.tsx       # Summary + issues + severity badges + fix commands
│   │   └── History.tsx      # Past analyses list
│   └── components/
│       ├── ProgressTracker.tsx   # Animated WS-driven step list
│       └── Navbar.tsx
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── package.json
```

---

## Phase 1 — FastAPI Backend + Multi-Cloud Scanner Abstraction
*Implements Prompt 1 | Request Flow step ③*

### Tasks

1. **`backend/scanners/base.py`** — Abstract `CloudScanner` interface:
   ```python
   class CloudScanner(ABC):
       @abstractmethod
       def list_scopes(self) -> list[dict]: ...        # RG / Account+Region / Project
       @abstractmethod
       def list_resources(self, scope: str) -> list[dict]: ...  # name, type, location, sku, tags
   ```

2. **`backend/scanners/azure.py`** — `AzureScanner(CloudScanner)`:
   - `list_scopes()` → `az group list -o json`
   - `list_resources(scope)` → `az resource list --resource-group <scope> -o json`
   - Internal `_run_az(args)` helper with typed exceptions:
     `AzureCLINotInstalledError`, `AzureCLINotLoggedInError`, `ResourceGroupNotFoundError`
   - Detect "not installed" via `FileNotFoundError`; "not logged in" via stderr containing `az login`; missing RG via `az group exists`.

3. **`backend/scanners/aws.py`** — `AWSScanner(CloudScanner)` (stub):
   - `list_scopes()` → `aws ec2 describe-regions` (returns account+region pairs)
   - `list_resources(scope)` → `aws resourcegroupstaggingapi get-resources --region <scope>`
   - Typed exceptions: `AWSCLINotInstalledError`, `AWSNotLoggedInError`

4. **`backend/scanners/gcp.py`** — `GCPScanner(CloudScanner)` (stub):
   - `list_scopes()` → `gcloud projects list --format=json`
   - `list_resources(scope)` → `gcloud asset search-all-resources --project=<scope>`
   - Typed exceptions: `GCloudCLINotInstalledError`, `GCloudNotLoggedInError`

5. **`backend/scanner_factory.py`**:
   ```python
   def get_scanner(provider: str) -> CloudScanner:
       match provider:
           case "azure": return AzureScanner()
           case "aws":   return AWSScanner()
           case "gcp":   return GCPScanner()
           case _:       raise ValueError(f"Unknown provider: {provider}")
   ```

6. **`backend/main.py`**:
   - FastAPI app, `CORSMiddleware` for `http://localhost:5173`
   - `GET /api/health`
   - `GET /api/scopes?provider=azure|aws|gcp` → calls `scanner.list_scopes()`
   - `POST /api/analyze` → accepts `{provider, scope}`, calls `scanner.list_resources(scope)`, returns structured list (AI wired in Phase 2)
   - `GET /api/providers` → returns `["azure", "aws", "gcp"]`

7. **`backend/requirements.txt`**: `fastapi`, `uvicorn[standard]`, `python-dotenv`

8. **`backend/.env.example`**: empty placeholder

### Verify Phase 1
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Azure (requires az login)
curl "http://localhost:8000/api/scopes?provider=azure"
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"provider":"azure","scope":"<your-rg>"}'

# Confirm error handling: missing provider → 400, CLI not installed → 503
```

---

## Phase 2 — OpenAI Cost Analysis
*Implements Prompt 2 | Request Flow step ⑤*

### Tasks

1. **`backend/ai_analyzer.py`** — `analyze_resources(provider: str, resources: list[dict]) -> dict`:
   - Builds system + user prompt with `provider` context so OpenAI understands the resource types.
   - Calls `gpt-4o` with `response_format={"type": "json_object"}`.
   - Returns strict JSON:
     ```json
     {
       "summary": "...",
       "issues": [
         {
           "resource_name": "...",
           "issue_type": "over-provisioned | unused | misconfigured | wrong-tier",
           "severity": "high | medium | low",
           "explanation": "...",
           "fix_command": "az vm resize ... | aws ec2 modify-instance-attribute ... | gcloud compute ..."
         }
       ],
       "estimated_savings": "$120/month"
     }
     ```
   - Raises `AIAnalysisError` on malformed/empty response.

2. **Update `POST /api/analyze`** in `main.py` to chain:
   `scanner.list_resources()` → `ai_analyzer.analyze_resources(provider, resources)` → return merged payload.

3. Update `requirements.txt`: add `openai`
4. Update `.env.example`: add `OPENAI_API_KEY=sk-...`

### Verify Phase 2
```bash
# Set OPENAI_API_KEY in .env, restart uvicorn
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"provider":"azure","scope":"<your-rg>"}'
# Response includes analysis.summary, analysis.issues[], analysis.estimated_savings
# Each issue has severity + fix_command
```

---

## Phase 3 — PostgreSQL Persistence + WebSocket Progress
*Implements Prompt 3 | Request Flow steps ④ and ⑥*

### Tasks

1. **`backend/db.py`** (asyncpg):
   - `init_db()` creates tables:
     ```sql
     users (
       id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       email        TEXT UNIQUE NOT NULL,
       password_hash TEXT NOT NULL,
       created_at   TIMESTAMPTZ DEFAULT now()
     )

     analyses (
       id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id           UUID REFERENCES users(id),
       cloud_provider    TEXT NOT NULL,        -- azure | aws | gcp
       scope             TEXT NOT NULL,        -- resource group / region / project
       resources_scanned INT,
       issues_found      INT,
       estimated_savings TEXT,
       analysis_result   JSONB,
       status            TEXT DEFAULT 'pending',
       created_at        TIMESTAMPTZ DEFAULT now()
     )
     ```
   - `get_pool()` → cached `asyncpg.Pool` from `DATABASE_URL`
   - Helpers: `insert_analysis(...)`, `update_analysis(id, result, status)`,
     `get_analyses_for_user(user_id)`, `get_analysis_by_id(id, user_id)`
   - Call `init_db()` from FastAPI `lifespan` startup event.

2. **Refactor `POST /api/analyze`** to BackgroundTask + WS pattern:
   - Insert `analyses` row with `status='pending'`, return `{analysis_id}` (HTTP 202).
   - `BackgroundTasks.add_task(run_analysis, analysis_id, provider, scope, user_id)` runs:
     1. `"Fetching available scopes..."` → push to WS
     2. `"Scanning resources in <scope>..."` → push to WS
     3. `"Analyzing costs with AI..."` → push to WS
     4. `"Storing results..."` → push to WS
     5. `"Analysis complete"` → push to WS, close WS connections
   - Progress is pushed to `_ws_connections: dict[str, list[WebSocket]]` (in-memory).

3. **`WS /ws/progress/{analysis_id}`**:
   - On connect: register socket; replay current DB status if already in-progress.
   - On disconnect: remove from dict.
   - **Auth:** validate JWT via `?token=<jwt>` query parameter.

4. Add `GET /api/analyses/{id}` for Report page to fetch a single result.

5. Update `requirements.txt`: add `asyncpg`
6. Update `.env.example`: add `DATABASE_URL=postgresql://user:pass@host:5432/dbname`

> **Local dev tip:** Run a local Postgres with Docker:
> ```bash
> docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=aiops postgres:16
> # DATABASE_URL=postgresql://postgres:secret@localhost:5432/aiops
> ```

### Verify Phase 3
```bash
# Start server, confirm tables created
uvicorn main:app --reload

# Trigger analysis (no auth yet)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"provider":"azure","scope":"<your-rg>"}'
# Returns {"analysis_id": "..."}  immediately (202)

# Watch progress
npx wscat -c "ws://localhost:8000/ws/progress/<analysis_id>"
# Fetching... → Scanning... → Analyzing... → Storing... → Analysis complete

# Confirm DB row has analysis_result populated and status='complete'
```

---

## Phase 4 — Custom JWT Auth (Backend) + React Frontend
*Implements Prompt 4 | Request Flow step ① + UI layer*

### Backend Auth

1. **`backend/auth.py`**:
   - `POST /api/auth/signup` → bcrypt-hash password, insert into `users`, return `{token}`
   - `POST /api/auth/login` → verify bcrypt hash, return `{token}`
   - `get_current_user` FastAPI dependency: decode JWT from `Authorization: Bearer <token>`, look up user in DB, raise 401 on invalid/expired.
   - Protect all `/api/*` routes (except `/api/health`, `/api/auth/*`) with `get_current_user`.

2. Update `requirements.txt`: add `PyJWT`, `bcrypt`
3. Update `.env.example`: add `JWT_SECRET=your-secret-here`

### Frontend Scaffold

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom axios
```

**`src/api.ts`** — Axios instance:
- `baseURL: http://localhost:8000`
- Request interceptor: attaches `Authorization: Bearer <token>` from `localStorage`
- Response interceptor: on 401 → clear token, redirect to `/login`

**`src/auth.tsx`** — `AuthProvider` context:
- State: `token`, `user`
- Methods: `login(email, password)`, `signup(email, password)`, `logout()`
- On load: validate token from `localStorage`; redirect to `/login` if absent/expired

### Pages

| Page | Route | What it does |
|---|---|---|
| `Login.tsx` | `/login` | Email + password form → `POST /api/auth/login` → store JWT |
| `Signup.tsx` | `/signup` | Email + password form → `POST /api/auth/signup` → store JWT |
| `Dashboard.tsx` | `/dashboard` | Cloud provider selector (Azure/AWS/GCP) + scope dropdown (from `GET /api/scopes?provider=`) + "Run Analysis" button + `<ProgressTracker>` |
| `Report.tsx` | `/report/:id` | Summary card (resources scanned, issues found, estimated savings) + issues with severity badges (🔴 high / 🟡 medium / 🟢 low) + copyable fix commands |
| `History.tsx` | `/history` | Table of past analyses (provider, scope, date, issues count, savings) → click to `/report/:id` |

### Components

- **`ProgressTracker.tsx`** — connects to `ws://localhost:8000/ws/progress/{id}?token=<jwt>`, renders animated step list as messages arrive; transitions to "View Report" button on complete.
- **`Navbar.tsx`** — logo + nav links (Dashboard, History) + Logout button.

**`src/App.tsx`** — Routes with a `<PrivateRoute>` wrapper that redirects to `/login` if no token.

### Verify Phase 4
```bash
cd frontend && npm run dev
# App loads at http://localhost:5173
# Signup → login → JWT in localStorage → Dashboard accessible
# GET /api/scopes?provider=azure populates dropdown
# Logout clears token → /dashboard redirects to /login
```

---

## Phase 5 — End-to-End Integration & Testing
*Implements Prompt 5 | Request Flow steps ①–⑦*

### Tasks

1. **Dashboard "Run Analysis"** full wiring:
   - `POST /api/analyze` with `{provider, scope}` + JWT → `{analysis_id}`
   - Open `ws://localhost:8000/ws/progress/{analysis_id}?token=<jwt>`
   - Stream into `<ProgressTracker>`; on `"Analysis complete"` navigate to `/report/:analysis_id`

2. **Report page** fetches `GET /api/analyses/{id}` and renders:
   - Summary card: total resources scanned, issues found, estimated savings
   - Per-issue: resource name, issue type, severity badge, explanation, copyable fix command
   - "Back to History" link

3. **History page** fetches `GET /api/history` → list → click row → `/report/:id`

4. **Full E2E manual test checklist:**
   - [ ] Signup with new email
   - [ ] Login with same credentials
   - [ ] Dashboard loads; cloud provider selector works; scope dropdown populates per provider
   - [ ] Run Analysis: progress streams live in correct order
   - [ ] Report displays correct summary, issues, fix commands
   - [ ] History shows the completed analysis
   - [ ] Click history item → opens same report from DB
   - [ ] Refresh Report page → still loads (data from DB, not in-memory)
   - [ ] Logout → `/dashboard` redirects to `/login`
   - [ ] Invalid JWT on protected endpoint → 401 → frontend redirects to `/login`
   - [ ] Test each cloud provider error path (CLI not installed → clear 503 message)

---

## Decisions Summary

| Decision | Choice | Reason |
|---|---|---|
| DB driver | asyncpg | Async — fits FastAPI's event loop |
| Analysis flow | POST → 202 + BackgroundTask + WS | Non-blocking; live progress to UI |
| Backend structure | Flat + `scanners/` sub-package | Matches prompts; clean multi-cloud abstraction |
| Auth module | `auth.py` (separate from `main.py`) | Keeps `main.py` readable; still flat |
| WS auth | JWT via `?token=` query param | Browser WS can't set headers |
| Scope | Local dev only | Azure PG + OpenAI + cloud CLIs via env vars |
| Multi-cloud | `CloudScanner` abstract base from Phase 1 | Avoids a big rewrite later; AWS/GCP stubs ready to flesh out |

---

## Open Considerations

1. **AWS/GCP stubs in Phase 1** — AWS and GCP scanners are created as stubs that return a clear `NotImplementedError` / 501. This lets the multi-cloud selector exist in the UI from the start without blocking Azure delivery. Full AWS/GCP implementation is a separate track after Phase 5.

2. **Local Postgres for dev** — Azure Managed PG may not be reachable from a local dev machine. Use the Docker command in Phase 3 with the same `DATABASE_URL` format; no code change required when pointing at Azure PG in production.

3. **OpenAI cost per run** — Each analysis call sends all resource data to `gpt-4o`. For large resource groups (100+ resources), consider chunking resources into batches or switching to `gpt-4o-mini` for dev to reduce cost during testing.
