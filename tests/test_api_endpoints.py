#!/usr/bin/env python3
"""
Unit tests for API Endpoints
============================

Covers essential API functionality:
- ✅ POST /labels/print (job submission validation)
- 📋 GET /labels/templates (template listing)
- 🔄 GET /labels/jobs/{job_id}/stream (SSE streaming)
- ❌ Basic error handling
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_manager import JobManager


class TestAPIEndpoints:

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)

    def test_submit_labels_invalid_template_name(self, client):
        """❌ Should reject invalid template name."""
        request_data = {
            "template_name": "invalid.txt",  # Not .glabels
            "data": [{"ITEM": "A001"}],
            "copies": 1,
        }

        response = client.post("/labels/print", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "template_name must have .glabels extension" in str(data)


class TestSSEEndpoint:
    """Tests for Server-Sent Events streaming endpoint"""

    @pytest.fixture
    def client_with_state(self):
        """Create test client with job_manager initialized."""
        # Initialize job_manager in app state for testing
        app.state.job_manager = JobManager()
        client = TestClient(app)
        yield client
        # Cleanup
        del app.state.job_manager

    def test_stream_job_not_found(self, client_with_state):
        """❌ SSE should return 404 for non-existent job"""
        response = client_with_state.get("/labels/jobs/nonexistent-job-id/stream")
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    def test_stream_completed_job(self, client_with_state):
        """🔄 SSE should stream status and close for completed job"""
        from datetime import datetime

        # Add a completed job to job_manager
        jm = app.state.job_manager
        job_id = "test-completed-job"
        jm.jobs[job_id] = {
            "status": "done",
            "filename": "test.pdf",
            "template": "demo.glabels",
            "error": None,
            "created_at": datetime.now(),
            "started_at": datetime.now(),
            "finished_at": datetime.now(),
            "request": {"template_name": "demo.glabels", "data": [], "copies": 1},
        }

        # Stream should return event-stream content type
        response = client_with_state.get(f"/labels/jobs/{job_id}/stream")

        # For completed jobs, SSE returns immediately with final status
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        # Check response contains status event
        content = response.text
        assert "event: status" in content
        assert '"status": "done"' in content or '"status":"done"' in content

    def test_stream_failed_job(self, client_with_state):
        """🔄 SSE should stream error status for failed job"""
        from datetime import datetime

        jm = app.state.job_manager
        job_id = "test-failed-job"
        jm.jobs[job_id] = {
            "status": "failed",
            "filename": "failed_job.pdf",  # filename is set even for failed jobs
            "template": "demo.glabels",
            "error": "Test error message",
            "created_at": datetime.now(),
            "started_at": datetime.now(),
            "finished_at": datetime.now(),
            "request": {"template_name": "demo.glabels", "data": [], "copies": 1},
        }

        response = client_with_state.get(f"/labels/jobs/{job_id}/stream")

        assert response.status_code == 200
        content = response.text
        assert "event: status" in content
        assert '"status": "failed"' in content or '"status":"failed"' in content
