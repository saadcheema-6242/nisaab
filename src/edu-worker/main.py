import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import get_settings
from edu_core.services.search import SearchService
from edu_core.storage import create_storage
from edu_db.session import init_db
from edu_queue.schemas import TaskType
from edu_queue.service import ClaimedJob, JobStore
from processors.registry import ProcessorRegistry
from rich.console import Console

console = Console(force_terminal=True)

# Check for jobs abandoned by a crashed worker about every 5 minutes
STALE_CHECK_INTERVAL_SECONDS = 300
# A drain keeps waiting for retries due within this many seconds
RETRY_WAIT_SECONDS = 120
# A drain stops by then so it ends before Cloud Scheduler's 30 minute deadline
DRAIN_MAX_SECONDS = 25 * 60


def run_job(job: ClaimedJob, registry: ProcessorRegistry, jobs: JobStore) -> None:
    """Run one claimed job and record the outcome.

    Args:
        job: The claimed job
        registry: ProcessorRegistry for getting processors
        jobs: Job store used to record success or failure
    """
    console.log(
        f"Running {job.type} job {job.id} "
        f"(attempt {job.attempts}/{job.max_attempts}, "
        f"project {job.payload.get('project_id', 'N/A')})"
    )
    try:
        processor = registry.get_processor(TaskType(job.type))
        asyncio.run(processor.process(job.payload))
        jobs.complete(job.id)
        console.log(f"Completed {job.type} job {job.id}")
    except Exception as e:
        retry = jobs.fail(job, f"{type(e).__name__}: {e}")
        outcome = "will retry" if retry else "giving up"
        console.print(f"[bold red]Job {job.id} failed ({outcome}): {e}[/bold red]")


def drain(
    registry: ProcessorRegistry,
    jobs: JobStore,
    executor: ThreadPoolExecutor,
    concurrency: int,
    poll_interval: float,
) -> int:
    """Process queued jobs until none are due soon, then return how many ran.

    Keeps waiting while a retry is due within RETRY_WAIT_SECONDS, and stops after
    DRAIN_MAX_SECONDS so the request finishes before Cloud Scheduler's deadline.
    """
    jobs.requeue_stale()
    processed = 0
    deadline = time.monotonic() + DRAIN_MAX_SECONDS
    while time.monotonic() < deadline:
        claimed = jobs.claim(limit=concurrency)
        if claimed:
            wait([executor.submit(run_job, job, registry, jobs) for job in claimed])
            processed += len(claimed)
        elif jobs.has_queued_due_within(RETRY_WAIT_SECONDS):
            time.sleep(poll_interval)
        else:
            break
    return processed


def start_http_server(port: int, drain_jobs) -> ThreadingHTTPServer:
    """Serve GET /health and POST /drain (called by Cloud Scheduler on Cloud Run)."""

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            self._reply(200, {"status": "ok"})

        def do_POST(self):  # noqa: N802
            if self.path.rstrip("/") != "/drain":
                self._reply(404, {"error": "not found"})
                return
            try:
                self._reply(200, {"processed": drain_jobs()})
            except Exception as e:
                console.print(f"[bold red]Drain failed: {e}[/bold red]")
                self._reply(500, {"error": str(e)})

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    console.print(f"HTTP endpoints (/health, POST /drain) listening on port {port}")
    return server


def main():
    settings = get_settings()

    init_db(settings.database_url)

    storage = create_storage(
        backend=settings.storage_backend,
        bucket=settings.storage_bucket,
        supabase_url=settings.supabase_url,
        supabase_service_role_key=settings.supabase_service_role_key,
    )
    storage.ensure_bucket()

    search_service = SearchService(
        database_url=settings.database_url,
        azure_openai_embedding_deployment=settings.azure_openai_embedding_deployment,
        azure_openai_endpoint=settings.azure_openai_endpoint,
        azure_openai_api_version=settings.azure_openai_api_version,
    )

    registry = ProcessorRegistry(
        search_service=search_service,
        storage=storage,
        azure_openai_chat_deployment=settings.azure_openai_chat_deployment,
        azure_openai_endpoint=settings.azure_openai_endpoint,
        azure_openai_api_version=settings.azure_openai_api_version,
        azure_cu_endpoint=settings.azure_cu_endpoint,
        azure_cu_key=settings.azure_cu_key,
        azure_cu_analyzer_id=settings.azure_cu_analyzer_id,
        azure_openai_embedding_deployment=settings.azure_openai_embedding_deployment,
    )

    jobs = JobStore()
    concurrency = max(1, settings.worker_concurrency)
    last_stale_check = 0.0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        server = None
        if settings.port:
            server = start_http_server(
                settings.port,
                lambda: drain(
                    registry, jobs, executor, concurrency, settings.worker_poll_interval
                ),
            )

        if not settings.worker_poll:
            if server is None:
                raise RuntimeError("WORKER_POLL=false needs PORT for the /drain endpoint")
            console.print(
                "[bold green]Worker started. Waiting for POST /drain...[/bold green]"
            )
            threading.Event().wait()

        console.print(
            f"[bold green]Worker started. Polling jobs (concurrency {concurrency})...[/bold green]"
        )
        while True:
            try:
                if time.monotonic() - last_stale_check > STALE_CHECK_INTERVAL_SECONDS:
                    if requeued := jobs.requeue_stale():
                        console.print(f"Requeued {requeued} stale job(s)")
                    last_stale_check = time.monotonic()

                claimed = jobs.claim(limit=concurrency)
            except Exception as e:
                # e.g. the database is briefly unreachable; keep the worker alive
                console.print(f"[bold red]Error polling jobs: {e}[/bold red]")
                time.sleep(settings.worker_poll_interval * 5)
                continue

            if not claimed:
                time.sleep(settings.worker_poll_interval)
                continue

            wait([executor.submit(run_job, job, registry, jobs) for job in claimed])


if __name__ == "__main__":
    main()
