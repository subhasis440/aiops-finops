# Changelog

All notable changes to this project should be documented in this file.

## 2026-06-22

### Added

1. Backend FastAPI implementation:
   - Authentication with JWT and bcrypt.
   - Protected APIs for providers, scopes, analysis, history, and report retrieval.
   - WebSocket progress channel by analysis id.
2. Cloud scanner abstraction and implementations:
   - Base interface in scanners/base.py.
   - Azure scanner using Azure CLI.
   - AWS scanner using AWS CLI.
   - GCP scanner using gcloud CLI.
3. AI analysis integration:
   - OpenAI chat completions workflow in ai_analyzer.py.
4. PostgreSQL persistence:
   - asyncpg pool, startup table creation, user and analysis data helpers.
5. Frontend application:
   - Vite + React + TypeScript + Tailwind setup.
   - Pages: Login, Signup, Dashboard, Report, History.
   - Components: Navbar, ProgressTracker.
   - API and auth context integration.
6. Project handoff documentation:
   - Added guide.md for setup and AI continuity.

### Verified

1. Backend source compiles successfully.
2. Frontend production build passes successfully.

### Notes

1. End-to-end execution requires valid .env values and cloud CLI authentication.
2. ripgrep is not available in this environment.

## Update template for future entries

Copy this block for each new date:

```md
## YYYY-MM-DD

### Added
1. ...

### Changed
1. ...

### Fixed
1. ...

### Verified
1. ...

### Notes
1. ...
```
