"""Infrastructure: In-memory async job store (fallback)."""
from __future__ import annotations

import time
from typing import Dict, Optional
from ulid import ULID

from src.application.dto.score_response import ScoreResponse
from src.infrastructure.jobs.job_store import JobStatus, JobState


class InMemoryJobStore:
    """Manages async job lifecycle in memory."""

    def __init__(self) -> None:
        self._jobs: Dict[str, dict] = {}

    async def enqueue(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        raw_jd: str,
        trace_id: str,
    ) -> str:
        job_id = str(ULID())
        self._jobs[job_id] = {
            "pdf_bytes": pdf_bytes.hex(),
            "filename": filename,
            "raw_jd": raw_jd,
            "trace_id": trace_id,
            "state": "pending",
            "created_at": time.time(),
        }
        return job_id

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        data = self._jobs.get(job_id)
        if not data:
            return None
        
        state: JobState = data.get("state", "pending")
        result_raw = data.get("result")
        result = ScoreResponse(**result_raw) if result_raw else None
        return JobStatus(state=state, result=result, error=data.get("error"))

    async def set_result(self, job_id: str, result: ScoreResponse) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["state"] = "done"
            self._jobs[job_id]["result"] = result.model_dump()

    async def set_failed(self, job_id: str, error: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["state"] = "failed"
            self._jobs[job_id]["error"] = error

    async def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def get_all_jds(self) -> list[str]:
        return list(set(j["raw_jd"] for j in self._jobs.values() if "raw_jd" in j and j["raw_jd"]))
