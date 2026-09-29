"""Background job queue stored in the Postgres ``jobs`` table."""

import logging
from dataclasses import dataclass
from typing import Any

from edu_db.models import Job
from edu_db.session import get_session_factory
from sqlalchemy import text

from .schemas import QueueTaskMessage

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
# Jobs still "running" after this long are assumed lost (e.g. the worker restarted)
STALE_AFTER_MINUTES = 30
# Wait before retrying a failed job: RETRY_DELAY_SECONDS * attempt number
RETRY_DELAY_SECONDS = 30


class QueueService:
    """Enqueues background jobs for the worker."""

    def send_message(
        self, message: QueueTaskMessage, max_attempts: int = DEFAULT_MAX_ATTEMPTS
    ) -> str:
        """Add a job to the queue.

        Args:
            message: The task type and its data
            max_attempts: How many times the job may run before it is marked failed

        Returns:
            The job ID
        """
        task_type = message["type"]
        job = Job(
            type=task_type.value if hasattr(task_type, "value") else str(task_type),
            payload=dict(message["data"]),
            max_attempts=max_attempts,
        )
        with get_session_factory()() as db:
            db.add(job)
            db.commit()
            logger.info("Queued job %s (%s)", job.id, job.type)
            return job.id


@dataclass
class ClaimedJob:
    """A job claimed by a worker."""

    id: str
    type: str
    payload: dict[str, Any]
    attempts: int
    max_attempts: int


class JobStore:
    """Claims and updates jobs for the worker."""

    def claim(self, limit: int) -> list[ClaimedJob]:
        """Claim up to ``limit`` queued jobs that are due, oldest first."""
        with get_session_factory()() as db:
            rows = db.execute(
                text(
                    """
                    UPDATE jobs
                    SET status = 'running', attempts = attempts + 1,
                        locked_at = now(), updated_at = now()
                    WHERE id IN (
                        SELECT id FROM jobs
                        WHERE status = 'queued' AND run_after <= now()
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT :limit
                    )
                    RETURNING id, type, payload, attempts, max_attempts
                    """
                ),
                {"limit": limit},
            ).all()
            db.commit()
            return [ClaimedJob(*row) for row in rows]

    def complete(self, job_id: str) -> None:
        """Mark a job as done."""
        self._execute(
            "UPDATE jobs SET status = 'done', locked_at = NULL, last_error = NULL,"
            " updated_at = now() WHERE id = :id",
            {"id": job_id},
        )

    def fail(self, job: ClaimedJob, error: str) -> bool:
        """Record a failure; requeue with a delay unless attempts are used up.

        Returns:
            True if the job will be retried
        """
        retry = job.attempts < job.max_attempts
        self._execute(
            """
            UPDATE jobs
            SET status = :status, last_error = :error, locked_at = NULL,
                run_after = now() + make_interval(secs => :delay), updated_at = now()
            WHERE id = :id
            """,
            {
                "id": job.id,
                "status": "queued" if retry else "failed",
                "error": error[:4000],
                "delay": RETRY_DELAY_SECONDS * job.attempts,
            },
        )
        return retry

    def has_queued_due_within(self, seconds: float) -> bool:
        """Whether a queued job becomes due within ``seconds`` (e.g. a pending retry)."""
        with get_session_factory()() as db:
            return bool(
                db.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM jobs WHERE status = 'queued'"
                        " AND run_after <= now() + make_interval(secs => :seconds))"
                    ),
                    {"seconds": seconds},
                ).scalar()
            )

    def requeue_stale(self) -> int:
        """Requeue jobs whose worker disappeared while running them."""
        return self._execute(
            """
            UPDATE jobs SET status = 'queued', locked_at = NULL, updated_at = now()
            WHERE status = 'running'
              AND locked_at < now() - make_interval(mins => :minutes)
            """,
            {"minutes": STALE_AFTER_MINUTES},
        )

    @staticmethod
    def _execute(sql: str, params: dict[str, Any]) -> int:
        with get_session_factory()() as db:
            result = db.execute(text(sql), params)
            db.commit()
            return result.rowcount
