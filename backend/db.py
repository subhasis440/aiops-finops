import asyncio
import json
import os
from typing import Any

import asyncpg

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is None:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise RuntimeError("DATABASE_URL is not configured.")
            _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                cloud_provider TEXT NOT NULL,
                scope TEXT NOT NULL,
                resources_scanned INT NOT NULL DEFAULT 0,
                issues_found INT NOT NULL DEFAULT 0,
                estimated_savings TEXT,
                analysis_result JSONB,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analyses_user_created
            ON analyses(user_id, created_at DESC);
            """
        )


def _row_to_dict(row: asyncpg.Record | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


async def create_user(email: str, password_hash: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash)
                VALUES ($1, $2)
                RETURNING id, email, created_at;
                """,
                email,
                password_hash,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ValueError("A user with this email already exists.") from exc

    user = _row_to_dict(row)
    if user is None:
        raise RuntimeError("User creation failed.")
    return user


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE email = $1;
            """,
            email,
        )
    return _row_to_dict(row)


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE id = $1;
            """,
            user_id,
        )
    return _row_to_dict(row)


async def create_analysis(user_id: str, cloud_provider: str, scope: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO analyses (user_id, cloud_provider, scope, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id, user_id, cloud_provider, scope, status, created_at;
            """,
            user_id,
            cloud_provider,
            scope,
        )

    analysis = _row_to_dict(row)
    if analysis is None:
        raise RuntimeError("Analysis creation failed.")
    return analysis


async def update_analysis_status(
    analysis_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE analyses
            SET status = $2,
                error_message = $3
            WHERE id = $1;
            """,
            analysis_id,
            status,
            error_message,
        )


async def complete_analysis(
    analysis_id: str,
    resources_scanned: int,
    issues_found: int,
    estimated_savings: str,
    analysis_result: dict[str, Any],
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE analyses
            SET resources_scanned = $2,
                issues_found = $3,
                estimated_savings = $4,
                analysis_result = $5::jsonb,
                status = 'complete',
                error_message = NULL
            WHERE id = $1;
            """,
            analysis_id,
            resources_scanned,
            issues_found,
            estimated_savings,
            json.dumps(analysis_result),
        )


async def fail_analysis(analysis_id: str, error_message: str) -> None:
    await update_analysis_status(analysis_id, "failed", error_message=error_message)


async def get_analyses_for_user(user_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                user_id,
                cloud_provider,
                scope,
                resources_scanned,
                issues_found,
                estimated_savings,
                analysis_result,
                status,
                error_message,
                created_at
            FROM analyses
            WHERE user_id = $1
            ORDER BY created_at DESC;
            """,
            user_id,
        )
    return [dict(row) for row in rows]


async def get_analysis_by_id(
    analysis_id: str,
    user_id: str | None = None,
) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            row = await conn.fetchrow(
                """
                SELECT
                    id,
                    user_id,
                    cloud_provider,
                    scope,
                    resources_scanned,
                    issues_found,
                    estimated_savings,
                    analysis_result,
                    status,
                    error_message,
                    created_at
                FROM analyses
                WHERE id = $1 AND user_id = $2;
                """,
                analysis_id,
                user_id,
            )
        else:
            row = await conn.fetchrow(
                """
                SELECT
                    id,
                    user_id,
                    cloud_provider,
                    scope,
                    resources_scanned,
                    issues_found,
                    estimated_savings,
                    analysis_result,
                    status,
                    error_message,
                    created_at
                FROM analyses
                WHERE id = $1;
                """,
                analysis_id,
            )

    return _row_to_dict(row)
