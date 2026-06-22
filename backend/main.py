import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import auth
import db
from ai_analyzer import AIAnalysisError, analyze_resources
from scanner_factory import get_scanner
from scanners import CLINotInstalledError, NotLoggedInError, ScopeNotFoundError
from scanners.base import ScannerError

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db()
    yield
    await db.close_pool()


app = FastAPI(title="AI Cloud Cost Detective API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    email: str
    password: str


class AnalyzeRequest(BaseModel):
    provider: str = "azure"
    scope: str | None = None
    resource_group: str | None = None

    def resolved_scope(self) -> str | None:
        return self.scope or self.resource_group


_ws_connections: dict[str, set[WebSocket]] = {}
_ws_lock = asyncio.Lock()


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or "." not in normalized.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    return normalized


def _validate_password(password: str) -> str:
    value = password.strip()
    if len(value) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    return value


def _status_to_message(status_value: str, scope: str) -> str:
    messages = {
        "pending": "Analysis queued",
        "fetching_scopes": "Fetching available scopes...",
        "scanning_resources": f"Scanning resources in {scope}...",
        "analyzing_costs": "Analyzing costs with AI...",
        "storing_results": "Storing results...",
        "complete": "Analysis complete",
        "failed": "Analysis failed",
    }
    return messages.get(status_value, "Processing...")


def _serialize_analysis(record: dict[str, Any]) -> dict[str, Any]:
    data = dict(record)
    data["id"] = str(data.get("id"))
    if data.get("user_id") is not None:
        data["user_id"] = str(data["user_id"])
    created_at = data.get("created_at")
    if isinstance(created_at, datetime):
        data["created_at"] = created_at.isoformat()
    data["resource_group"] = data.get("scope")
    return data


def _raise_http_from_scanner_error(exc: Exception) -> None:
    if isinstance(exc, CLINotInstalledError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, NotLoggedInError):
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if isinstance(exc, ScopeNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _register_ws(analysis_id: str, websocket: WebSocket) -> None:
    async with _ws_lock:
        _ws_connections.setdefault(analysis_id, set()).add(websocket)


async def _unregister_ws(analysis_id: str, websocket: WebSocket) -> None:
    async with _ws_lock:
        sockets = _ws_connections.get(analysis_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            _ws_connections.pop(analysis_id, None)


async def _broadcast_progress(analysis_id: str, message: str, status_value: str) -> None:
    async with _ws_lock:
        sockets = list(_ws_connections.get(analysis_id, set()))

    stale: list[WebSocket] = []
    payload = {
        "analysis_id": analysis_id,
        "status": status_value,
        "message": message,
    }
    for socket in sockets:
        try:
            await socket.send_json(payload)
        except Exception:  # noqa: BLE001
            stale.append(socket)

    for socket in stale:
        await _unregister_ws(analysis_id, socket)


async def _set_status(analysis_id: str, status_value: str, message: str) -> None:
    await db.update_analysis_status(analysis_id, status_value)
    await _broadcast_progress(analysis_id, message, status_value)


async def run_analysis_task(analysis_id: str, provider: str, scope: str) -> None:
    try:
        scanner = get_scanner(provider)

        await _set_status(analysis_id, "fetching_scopes", "Fetching available scopes...")
        await asyncio.to_thread(scanner.list_scopes)

        scanning_message = f"Scanning resources in {scope}..."
        await _set_status(analysis_id, "scanning_resources", scanning_message)
        resources = await asyncio.to_thread(scanner.list_resources, scope)

        await _set_status(analysis_id, "analyzing_costs", "Analyzing costs with AI...")
        analysis = await asyncio.to_thread(analyze_resources, provider, resources)

        await _set_status(analysis_id, "storing_results", "Storing results...")
        issues = analysis.get("issues", []) if isinstance(analysis, dict) else []
        issues_found = len(issues) if isinstance(issues, list) else 0
        estimated_savings = str(analysis.get("estimated_savings", "$0/month"))
        await db.complete_analysis(
            analysis_id=analysis_id,
            resources_scanned=len(resources),
            issues_found=issues_found,
            estimated_savings=estimated_savings,
            analysis_result=analysis,
        )

        await _broadcast_progress(analysis_id, "Analysis complete", "complete")
    except (ScopeNotFoundError, ScannerError, AIAnalysisError) as exc:
        await db.fail_analysis(analysis_id, str(exc))
        await _broadcast_progress(analysis_id, f"Analysis failed: {exc}", "failed")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected analysis failure for %s", analysis_id)
        await db.fail_analysis(analysis_id, str(exc))
        await _broadcast_progress(analysis_id, f"Analysis failed: {exc}", "failed")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/signup")
async def signup(payload: AuthRequest) -> dict[str, Any]:
    email = _validate_email(payload.email)
    password = _validate_password(payload.password)

    password_hash = auth.hash_password(password)
    try:
        user = await db.create_user(email=email, password_hash=password_hash)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    token = auth.create_access_token(user_id=str(user["id"]), email=user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
        },
    }


@app.post("/api/auth/login")
async def login(payload: AuthRequest) -> dict[str, Any]:
    email = _validate_email(payload.email)
    password = payload.password

    user = await db.get_user_by_email(email)
    if not user or not auth.verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = auth.create_access_token(user_id=str(user["id"]), email=user["email"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
        },
    }


@app.get("/api/providers")
async def providers(_: dict[str, Any] = Depends(auth.get_current_user)) -> dict[str, list[str]]:
    return {"providers": ["azure", "aws", "gcp"]}


@app.get("/api/scopes")
async def list_scopes(
    provider: str = Query(default="azure"),
    _: dict[str, Any] = Depends(auth.get_current_user),
) -> dict[str, Any]:
    try:
        scanner = get_scanner(provider)
        scopes = await asyncio.to_thread(scanner.list_scopes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        _raise_http_from_scanner_error(exc)

    return {
        "provider": provider,
        "scopes": scopes,
    }


@app.get("/api/resource-groups")
async def list_resource_groups(
    _: dict[str, Any] = Depends(auth.get_current_user),
) -> dict[str, Any]:
    try:
        scanner = get_scanner("azure")
        scopes = await asyncio.to_thread(scanner.list_scopes)
    except Exception as exc:  # noqa: BLE001
        _raise_http_from_scanner_error(exc)

    return {
        "resource_groups": [scope.get("name") for scope in scopes if scope.get("name")],
        "items": scopes,
    }


@app.post("/api/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze(
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(auth.get_current_user),
) -> dict[str, Any]:
    provider = payload.provider.strip().lower() if payload.provider else "azure"
    scope = payload.resolved_scope()
    if not scope:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'scope' or 'resource_group' in request body.",
        )

    try:
        get_scanner(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis = await db.create_analysis(
        user_id=str(current_user["id"]),
        cloud_provider=provider,
        scope=scope,
    )

    analysis_id = str(analysis["id"])
    background_tasks.add_task(run_analysis_task, analysis_id, provider, scope)

    return {
        "analysis_id": analysis_id,
        "status": "pending",
    }


@app.get("/api/history")
async def history(current_user: dict[str, Any] = Depends(auth.get_current_user)) -> dict[str, Any]:
    rows = await db.get_analyses_for_user(str(current_user["id"]))
    return {
        "analyses": [_serialize_analysis(row) for row in rows],
    }


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: dict[str, Any] = Depends(auth.get_current_user),
) -> dict[str, Any]:
    row = await db.get_analysis_by_id(analysis_id, user_id=str(current_user["id"]))
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return _serialize_analysis(row)


@app.websocket("/ws/progress/{analysis_id}")
async def websocket_progress(
    websocket: WebSocket,
    analysis_id: str,
    token: str | None = Query(default=None),
):
    if not token:
        await websocket.close(code=4401)
        return

    try:
        user = await auth.get_current_user_from_token(token)
        analysis = await db.get_analysis_by_id(analysis_id, user_id=str(user["id"]))
    except HTTPException:
        await websocket.close(code=4401)
        return

    if not analysis:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await _register_ws(analysis_id, websocket)

    status_value = str(analysis.get("status", "pending"))
    message = _status_to_message(status_value, str(analysis.get("scope", "")))
    if status_value == "failed" and analysis.get("error_message"):
        message = f"Analysis failed: {analysis.get('error_message')}"

    await websocket.send_json(
        {
            "analysis_id": analysis_id,
            "status": status_value,
            "message": message,
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _unregister_ws(analysis_id, websocket)
