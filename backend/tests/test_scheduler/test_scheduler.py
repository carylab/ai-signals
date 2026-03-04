"""
Tests for the scheduler, retry, and health modules.

These tests are pure-Python (no network, no DB) and run in the test
asyncio event loop provided by pytest-asyncio.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.scheduler.retry import run_with_retry
from app.scheduler.health import PipelineHealthMonitor


# ── run_with_retry ─────────────────────────────────────────────────────────────

class TestRunWithRetry:
    async def test_success_first_attempt(self):
        calls = []

        async def ok():
            calls.append(1)
            return "done"

        result = await run_with_retry(ok, max_attempts=3, base_delay=0)
        assert result == "done"
        assert len(calls) == 1

    async def test_retries_on_failure_then_succeeds(self):
        attempts = []

        async def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("transient")
            return "ok"

        result = await run_with_retry(flaky, max_attempts=3, base_delay=0)
        assert result == "ok"
        assert len(attempts) == 3

    async def test_raises_after_max_attempts(self):
        async def always_fails():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await run_with_retry(always_fails, max_attempts=3, base_delay=0)

    async def test_keyboard_interrupt_not_retried(self):
        calls = []

        async def raise_ki():
            calls.append(1)
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            await run_with_retry(raise_ki, max_attempts=3, base_delay=0)

        assert len(calls) == 1  # no retry

    async def test_passes_args_and_kwargs(self):
        async def fn(a, b, *, c):
            return a + b + c

        result = await run_with_retry(fn, 1, 2, max_attempts=1, base_delay=0, c=10)
        assert result == 13

    async def test_single_attempt_no_retry(self):
        async def fails():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await run_with_retry(fails, max_attempts=1, base_delay=0)


# ── PipelineHealthMonitor ─────────────────────────────────────────────────────

class TestPipelineHealthMonitor:
    def _make_record(self, status="success", **kwargs):
        defaults = dict(
            run_id="abc",
            started_at=datetime.now(timezone.utc),
            status=status,
            duration_s=120.0,
            collected=100,
            published=80,
            errors=0,
        )
        defaults.update(kwargs)
        return defaults

    def test_empty_summary(self):
        m = PipelineHealthMonitor()
        s = m.summary()
        assert s["recent_runs"] == 0
        assert s["last_run"] is None

    def test_single_success(self):
        m = PipelineHealthMonitor()
        m.record(**self._make_record(status="success"))
        s = m.summary()
        assert s["recent_runs"] == 1
        assert s["success_rate"] == 1.0
        assert s["last_run"]["status"] == "success"

    def test_success_rate_calculation(self):
        m = PipelineHealthMonitor()
        for status in ["success", "success", "failed", "success"]:
            m.record(**self._make_record(status=status))
        s = m.summary()
        assert s["success_rate"] == pytest.approx(0.75)

    def test_ring_buffer_cap(self):
        m = PipelineHealthMonitor()
        m._MAX_RECORDS = 5
        m._records.maxlen  # deque is created in __init__, need to recreate
        from collections import deque
        m._records = deque(maxlen=5)

        for i in range(10):
            m.record(**self._make_record(run_id=str(i)))

        assert m.summary()["recent_runs"] == 5
        # last run_id should be "9"
        assert m.summary()["last_run"]["run_id"] == "9"

    def test_last_run_fields(self):
        m = PipelineHealthMonitor()
        m.record(
            run_id="xyz",
            started_at=datetime(2026, 3, 4, 6, 0, tzinfo=timezone.utc),
            status="partial",
            duration_s=300.5,
            collected=200,
            published=150,
            errors=3,
        )
        lr = m.summary()["last_run"]
        assert lr["run_id"] == "xyz"
        assert lr["status"] == "partial"
        assert lr["duration_s"] == 300.5
        assert lr["collected"] == 200
        assert lr["published"] == 150
        assert lr["errors"] == 3


# ── Scheduler worker ─────────────────────────────────────────────────────────

class TestSchedulerWorker:
    async def test_trigger_now_raises_when_locked(self):
        """trigger_now should raise RuntimeError if a run is already in progress."""
        import app.scheduler.worker as w

        original_lock = w._run_lock
        # Simulate locked state
        locked = asyncio.Lock()
        await locked.acquire()
        w._run_lock = locked

        try:
            with pytest.raises(RuntimeError, match="already in progress"):
                await w.trigger_now()
        finally:
            locked.release()
            w._run_lock = original_lock

    async def test_scheduler_status_structure(self):
        """scheduler_status() returns expected keys."""
        from app.scheduler.worker import scheduler_status
        s = scheduler_status()
        assert "enabled" in s
        assert "cron" in s
        assert "running" in s
        assert "last_run_at" in s
        assert "next_run_at" in s
        assert "health" in s

    async def test_pipeline_job_skips_if_locked(self, caplog):
        """If lock is already held, _pipeline_job returns without doing anything."""
        import app.scheduler.worker as w

        original_lock = w._run_lock
        locked = asyncio.Lock()
        await locked.acquire()
        w._run_lock = locked

        try:
            # Should return immediately without error
            await w._pipeline_job()
        finally:
            locked.release()
            w._run_lock = original_lock
