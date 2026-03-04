"""
Health monitoring for the scheduler / worker.

Tracks pipeline run history and exposes summary metrics so the /stats
endpoint can surface pipeline health without hitting the database.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Optional


@dataclass
class RunRecord:
    run_id:     str
    started_at: datetime
    status:     str          # "success" | "partial" | "failed"
    duration_s: float
    collected:  int
    published:  int
    errors:     int


class PipelineHealthMonitor:
    """
    In-memory ring-buffer of recent run records.

    Kept to the last 48 runs (~2 days of daily + ad-hoc runs).
    """

    _MAX_RECORDS = 48

    def __init__(self) -> None:
        self._records: Deque[RunRecord] = deque(maxlen=self._MAX_RECORDS)

    def record(
        self,
        *,
        run_id: str,
        started_at: datetime,
        status: str,
        duration_s: float,
        collected: int,
        published: int,
        errors: int,
    ) -> None:
        self._records.append(
            RunRecord(
                run_id=run_id,
                started_at=started_at,
                status=status,
                duration_s=duration_s,
                collected=collected,
                published=published,
                errors=errors,
            )
        )

    def summary(self) -> dict:
        """Return a JSON-serialisable summary dict."""
        if not self._records:
            return {"recent_runs": 0, "last_run": None, "success_rate_7d": None}

        total = len(self._records)
        successes = sum(1 for r in self._records if r.status == "success")
        last = self._records[-1]

        return {
            "recent_runs":      total,
            "success_rate":     round(successes / total, 3),
            "last_run": {
                "run_id":      last.run_id,
                "started_at":  last.started_at.isoformat(),
                "status":      last.status,
                "duration_s":  last.duration_s,
                "collected":   last.collected,
                "published":   last.published,
                "errors":      last.errors,
            },
        }


# Module-level singleton used by scheduler and worker
health_monitor = PipelineHealthMonitor()
