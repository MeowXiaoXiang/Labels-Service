<!-- .github/copilot-instructions.md
Guidance for AI coding agents working on this repo.
Keep concise, actionable, and project-specific.
-->

# Quick Agent Notes — labels-service-open-source

Short, focused guidance to help an AI coding assistant be productive in this repository.

-   Project purpose: FastAPI microservice that wraps the gLabels CLI to convert JSON → CSV → gLabels → PDF. Core flow: app/main.py → JobManager → LabelPrintService → GlabelsEngine (app/utils/glabels_engine.py).

-   Key files to read first:

    -   `app/main.py` (FastAPI app, lifespan manages JobManager)
    -   `app/services/job_manager.py` (in-memory job store, asyncio queue, worker pool)
    -   `app/services/label_print.py` (JSON→CSV conversion, temp file policy, output naming)
    -   `app/utils/glabels_engine.py` (async subprocess wrapper for `glabels-3-batch`)
    -   `app/services/template_service.py` and `app/parsers/*` (template discovery and parsing)
    -   `app/models/dto.py` (pydantic models and validation rules)

-   Architecture & conventions (what to preserve):

    -   Jobs are stored in memory (`JobManager.jobs`); retention cleanup is time-based (`RETENTION_HOURS`). Avoid changing this semantics unless adding persistence.
    -   Concurrency is controlled in two layers: `JobManager.max_parallel` controls worker count; `GlabelsEngine` uses a semaphore for subprocess concurrency. Keep both in sync when modifying parallelism.
    -   File locations: `templates/` (read-only templates), `output/` (PDFs), `temp/` (optional CSV retention when `KEEP_CSV=true`). Do not hardcode absolute paths; use these relative directories.
    -   Template filenames must end with `.glabels`. Validation is enforced in `LabelRequest` model and `_resolve_template`.

-   Developer workflows & useful commands (verified in README):

    -   Local dev (Linux/WSL2):
        -   Copy env: `cp .env.example .env`
        -   Install deps: `pip install -r requirements.txt`
        -   Install gLabels: `sudo apt-get install glabels glabels-data`
        -   Run app: `python -m app.main`
    -   Docker (recommended): see `README.md` — `docker compose up -d` after copying `.env`.
    -   Tests: `pytest tests/` (unit tests mock subprocesses; running tests doesn't require gLabels binary).

-   Patterns and gotchas for edits and PRs:

    -   Tests frequently monkeypatch `asyncio.create_subprocess_exec` and `jm.service.generate_pdf`. When changing `GlabelsEngine.run_batch` or JobManager worker semantics, update tests accordingly.
    -   `GlabelsEngine.run_batch` raises typed errors: `GlabelsTimeoutError`, `GlabelsExecutionError` and `FileNotFoundError`. Preserve those exception types for callers to handle.
    -   `LabelPrintService._json_to_csv` relies on field ordering inferred by key appearance. If you change CSV behavior, update `tests/test_job_manager.py` and `tests/test_glabels_engine.py`.
    -   Logging uses `loguru` and a custom setup in `app/core/logger.py` — keep log messages' structure for consistency with tests and troubleshooting.

-   Small examples to follow when implementing changes:

    -   To add a new endpoint that enqueues a job, mimic `app/api/print_jobs.py:submit_labels` — validate `LabelRequest`, call `job_manager.submit_job(req)`, return `JobSubmitResponse`.
    -   To call glabels with extra args, use `LabelPrintService.generate_pdf(..., copies=n)` which passes `extra_args=["--copies=n"]` to `GlabelsEngine.run_batch`.

-   Where to look for integration points:

    -   Background workers lifecycle: `app.main:lifespan` starts/stops `JobManager` and workers.
    -   Template detection: `TemplateService._detect_format` parses gzipped `.glabels` XML and chooses parser type in `app/parsers`.

-   Safety & backward-compatibility rules for AI edits:
    1. Do not change public API routes or JSON model fields without updating `app/models/dto.py` and OpenAPI examples in `app/api/print_jobs.py`.
    2. Preserve exception classes and error messages used in tests (`Glabels*` errors and HTTP 404/409 cases).
    3. Keep default directories (`templates/`, `output/`, `temp/`) and env-driven flags (`KEEP_CSV`, `MAX_PARALLEL`, `GLABELS_TIMEOUT`, `AUTO_CLEANUP_PDF`).

If anything above is unclear or you want more examples (e.g., common PR templates or how to mock subprocesses in tests), tell me which area to expand.
