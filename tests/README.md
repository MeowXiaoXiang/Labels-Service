# Test Suite

Essential unit tests for the labels-service project, focusing on core functionality and business logic.

## Quick Start

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_glabels_engine.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Test Files Overview

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_glabels_engine.py` | 6 | Core CLI wrapper functionality |
| `test_job_manager.py` | 5 | Job lifecycle and worker management |
| `test_template_service.py` | 6 | Template discovery and parsing |
| `test_integration.py` | 4 | End-to-end workflows |
| `test_api_endpoints.py` | 1 | Basic API validation |

## Total: 22 focused tests

## What Each Test Covers

### `test_glabels_engine.py`

Tests the CLI wrapper that executes gLabels commands:

- ✅ Successful PDF generation
- ❌ Command failures and error handling  
- ⏱️ Timeout scenarios
- 📂 Missing files detection
- 🧵 Long error output truncation

### `test_job_manager.py`

Tests asynchronous job processing:

- 📥 Job submission and queuing
- ✅ Job completion tracking
- ❌ Error propagation and failure handling
- 🗑️ Automatic cleanup of old jobs
- 📋 Job status and listing

### `test_template_service.py`

Tests template file management:

- 📋 Template discovery in directories
- 🔍 Template info extraction
- 🏭 Format detection (CSV/TSV detection)
- ❌ Error handling for invalid templates
- 📂 Missing directory handling

### `test_integration.py`

Tests end-to-end workflows:

- 🔄 Template discovery workflow
- 📊 Template info retrieval process
- 🏭 Job manager integration
- ❌ Error propagation across components

### `test_api_endpoints.py`

Tests API input validation:

- ❌ Invalid template name rejection

## Testing Philosophy

This test suite follows a **focused testing** approach:

- ✅ **Test business logic**, not framework features
- 🎯 **Mock external dependencies** (filesystem, subprocess, network)
- ⚡ **Fast execution** - complete suite runs in under 1 second
- � **Easy maintenance** - tests focus on critical functionality

## Test Execution Tips

```bash
# Run all tests (recommended)
pytest tests/

# Run with detailed output
pytest tests/ -v

# Run specific component
pytest tests/test_job_manager.py

# Run with coverage
pytest tests/ --cov=app
```

## Development Notes

- Tests use extensive mocking to isolate components
- Integration tests verify end-to-end workflows
- Focus is on core business logic validation
- External dependencies are mocked for reliability
