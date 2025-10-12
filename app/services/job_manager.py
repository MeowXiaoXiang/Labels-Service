# app/services/job_manager.py
# Job Manager: Task scheduling and worker pool
# - Handles job queue, worker assignment, and job cleanup
# - info logs: submission, completion, failure
# - debug logs: worker start, job execution, cleanup

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.config import settings
from app.models.dto import LabelRequest
from app.services.label_print import LabelPrintService


class JobManager:
    def __init__(self):
        # All job states (in-memory)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        # Async queue for job scheduling
        self.queue: asyncio.Queue = asyncio.Queue()
        # Worker task list
        self.workers: List[asyncio.Task] = []

        # Counter: total submitted jobs (lifetime, reset on restart)
        self.jobs_total: int = 0

        # Determine max concurrency
        if settings.MAX_PARALLEL in (0, None):
            self.max_parallel = max(1, (os.cpu_count() or 2) - 1)
        else:
            self.max_parallel = int(settings.MAX_PARALLEL)

        # Label print service instance
        self.service = LabelPrintService(
            max_parallel=self.max_parallel,
            default_timeout=settings.GLABELS_TIMEOUT,
            keep_csv=settings.KEEP_CSV,
        )

        # Job retention period (expired jobs will be removed)
        self.retention = timedelta(hours=settings.RETENTION_HOURS)

    # --------------------------------------------------------
    # Create job record
    # --------------------------------------------------------
    def _make_job(
        self, req: LabelRequest, job_id: str, filename: str
    ) -> Dict[str, Any]:
        """
        Create initial job record (pending status).
        """
        now = datetime.now()
        return {
            "status": "pending",
            "filename": filename,  # output filename (PDF)
            "template": req.template_name,  # gLabels template
            "error": None,
            "created_at": now,
            "updated_at": now,
            "request": req.model_dump(),
        }

    # --------------------------------------------------------
    # Worker loop
    # --------------------------------------------------------
    async def _worker(self, wid: int):
        """
        Worker loop:
        - Dequeue job
        - Call LabelPrintService.generate_pdf
        - Update job state
        """
        logger.info(f"[JobManager] Worker-{wid} started (max={self.max_parallel})")
        try:
            while True:
                job_id, req, filename = await self.queue.get()
                job = self.jobs[job_id]
                job["status"] = "running"
                job["updated_at"] = datetime.now()

                logger.debug(
                    f"[Worker-{wid}] 🚀 START job_id={job_id}, template={req.template_name}"
                )

                try:
                    await self.service.generate_pdf(
                        job_id=job_id,
                        template_name=req.template_name,
                        data=req.data,
                        copies=req.copies,
                        filename=filename,  # target output filename
                    )
                    job["status"] = "done"
                    logger.info(
                        f"[Worker-{wid}] ✅ job_id={job_id} completed → {filename}"
                    )
                except Exception as e:
                    job["status"] = "failed"
                    job["error"] = str(e)
                    logger.exception(f"[Worker-{wid}] ❌ job_id={job_id} failed")
                finally:
                    job["updated_at"] = datetime.now()
                    self.queue.task_done()
                    self._cleanup_jobs()
        except asyncio.CancelledError:
            logger.info(f"[Worker-{wid}] 🛑 stopped by cancel()")
            raise

    # --------------------------------------------------------
    # Cleanup expired jobs
    # --------------------------------------------------------
    def _cleanup_jobs(self):
        """
        Remove jobs older than retention period.
        Optionally cleanup associated PDF files.
        """
        cutoff = datetime.now() - self.retention
        old_jobs = [jid for jid, job in self.jobs.items() if job["created_at"] < cutoff]

        for jid in old_jobs:
            job = self.jobs[jid]

            # Cleanup PDF file if auto cleanup is enabled
            if settings.AUTO_CLEANUP_PDF and "output_file" in job:
                pdf_path = Path(job["output_file"])
                if pdf_path.exists():
                    try:
                        pdf_path.unlink()
                        logger.debug(f"[JobManager] 🗑️ deleted PDF: {pdf_path.name}")
                    except OSError as e:
                        logger.warning(
                            f"[JobManager] ⚠️ failed to delete PDF {pdf_path.name}: {e}"
                        )

            # Remove job from memory
            logger.debug(f"[JobManager] 🗑️ cleanup expired job_id={jid}")
            self.jobs.pop(jid, None)

    # --------------------------------------------------------
    # Worker pool management
    # --------------------------------------------------------
    def start_workers(self):
        """
        Start all workers to process the queue.
        """
        for wid in range(self.max_parallel):
            task = asyncio.create_task(self._worker(wid))
            self.workers.append(task)
        logger.info(f"[JobManager] started with {self.max_parallel} workers")

    async def stop_workers(self):
        """
        Stop all workers and wait for completion.
        """
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        logger.info("[JobManager] stopped")

    # --------------------------------------------------------
    # Public API methods
    # --------------------------------------------------------
    async def submit_job(self, req: LabelRequest) -> str:
        """
        Submit a new print job:
        - Generate job_id
        - Create output filename
        - Create job record
        - Enqueue for worker processing
        """
        job_id = str(uuid.uuid4())
        filename = self.service.make_output_filename(req.template_name)
        self.jobs[job_id] = self._make_job(req, job_id, filename)

        # Increment total submitted jobs counter
        self.jobs_total += 1

        await self.queue.put((job_id, req, filename))
        logger.info(
            f"[JobManager] 📨 submitted job_id={job_id}, template={req.template_name}"
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single job by job_id.
        """
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List the most recent N jobs.
        """
        items = list(self.jobs.items())
        items.sort(key=lambda kv: kv[1]["created_at"], reverse=True)
        return [dict(job_id=jid, **data) for jid, data in items[:limit]]
