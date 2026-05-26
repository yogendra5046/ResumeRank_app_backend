"""Infrastructure: Redis-backed async job store for >10s requests.

Jobs are enqueued with a ULID (sortable, URL-safe) as the job_id.
Status transitions: pending → processing → done | failed
Results stored as JSON in Redis with TTL=1h.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

import orjson
import redis.asyncio as aioredis
import structlog
from ulid import ULID

from src.application.dto.score_response import ScoreResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_JOB_TTL_SECONDS: int = 3600  # 1 hour
_JOB_KEY_PREFIX = "job:"

JobState = Literal["pending", "processing", "done", "failed"]


@dataclass
class JobStatus:
    state: JobState
    result: ScoreResponse | None = None
    error: str | None = None


class JobStore:
    """Manages async job lifecycle in Redis."""

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client

    async def enqueue(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        raw_jd: str,
        trace_id: str,
    ) -> str:
        """Create a pending job, store payload, return job_id."""
        job_id = str(ULID())
        payload = orjson.dumps(
            {
                "pdf_bytes": pdf_bytes.hex(),  # store as hex to avoid binary encoding issues
                "filename": filename,
                "raw_jd": raw_jd,
                "trace_id": trace_id,
                "state": "pending",
            }
        )
        await self._redis.setex(
            name=f"{_JOB_KEY_PREFIX}{job_id}",
            time=_JOB_TTL_SECONDS,
            value=payload,
        )
        logger.info("job_enqueued", job_id=job_id, trace_id=trace_id)
        return job_id

    async def get_status(self, job_id: str) -> JobStatus | None:
        raw = await self._redis.get(f"{_JOB_KEY_PREFIX}{job_id}")
        if raw is None:
            return None
        data: dict[str, object] = orjson.loads(raw)
        state: JobState = data.get("state", "pending")  # type: ignore[assignment]
        result_raw = data.get("result")
        result = ScoreResponse(**result_raw) if result_raw else None  # type: ignore[arg-type]
        return JobStatus(state=state, result=result, error=data.get("error"))  # type: ignore[arg-type]

    async def set_result(self, job_id: str, result: ScoreResponse) -> None:
        """Mark job done and store the ScoreResponse."""
        payload = orjson.dumps(
            {"state": "done", "result": result.model_dump()}
        )
        await self._redis.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL_SECONDS, payload)
        logger.info("job_completed", job_id=job_id, score=result.overall_score)

    async def set_failed(self, job_id: str, error: str) -> None:
        payload = orjson.dumps({"state": "failed", "error": error})
        await self._redis.setex(f"{_JOB_KEY_PREFIX}{job_id}", _JOB_TTL_SECONDS, payload)
        logger.error("job_failed", job_id=job_id, error=error)

    async def delete(self, job_id: str) -> None:
        await self._redis.delete(f"{_JOB_KEY_PREFIX}{job_id}")
        logger.info("job_deleted", job_id=job_id)

    async def get_all_jds(self) -> list[str]:
        """Scan for all active job keys and return unique JDs."""
        jds: list[str] = []
        async for key in self._redis.scan_iter(f"{_JOB_KEY_PREFIX}*"):
            raw = await self._redis.get(key)
            if raw:
                try:
                    data = orjson.loads(raw)
                    if "raw_jd" in data and data["raw_jd"]:
                        jds.append(data["raw_jd"])
                except Exception:
                    continue
        return list(set(jds)) # unique JDs
