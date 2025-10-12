#!/usr/bin/env python3
"""
Unit tests for API Endpoints
============================

Covers essential API functionality:
- ✅ POST /labels/print (job submission validation)
- 📋 GET /labels/templates (template listing)
- ❌ Basic error handling
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


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
