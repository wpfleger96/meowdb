# This file is managed by github-config. Do not edit manually.
# https://github.com/wpfleger96/github-config

# Settings
set dotenv-load := false

# Quick checks: sync, type-check, lint-check, format-check (no tests)
default: sync type-check lint-check format-check

# Install and sync project dependencies with uv
sync:
    uv sync

# Check types with mypy
type-check:
    uv run mypy .

# Check for lint issues (without fixing) with ruff
lint-check:
    uvx ruff check .

# Check code formatting (without fixing) with ruff
format-check:
    uvx ruff format . --check

# Fix lint issues with ruff
lint:
    uvx ruff check . --fix

# Auto-format code with ruff
format:
    uvx ruff format .

# Run quality checks: sync, type-check, lint-check, format-check
check: sync type-check lint-check format-check
    @echo "Quick quality checks passed"

# Run all quality checks (check) and unit+integration tests
check-all: check test
    @echo "All quality checks and tests passed"

# Pre-commit gate: sync, type-check, lint, format, and all tests
pre-commit: sync type-check lint format test
    @echo "Pre-commit checks passed"

# Run all unit and integration tests (excludes e2e)
test:
    uv run pytest -m "not e2e"

# Run unit tests only
test-unit:
    uv run pytest -m unit

# Run integration tests only
test-integration:
    uv run pytest -m integration

# Run end-to-end tests (no coverage)
test-e2e:
    uv run pytest -m e2e --no-cov || test $? -eq 5

# Run all tests including e2e (no coverage)
test-all:
    uv run pytest --no-cov

# Build distribution package (after syncing deps)
build: sync
    uv build

# Remove dist/, build/, and *.egg-info artifacts
clean-build:
    rm -rf dist/ build/ src/*.egg-info

# Clean build artifacts and rebuild the distribution package
rebuild: clean-build build

# CI gate: sync, type-check, lint-check, format-check, and tests
ci: sync type-check lint-check format-check test
    @echo "CI checks passed"

# Start dev server with password auth (password: test, secret: dev-secret)
dev-auth:
    #!/usr/bin/env bash
    set -euo pipefail
    HASH=$(uv run python -c "import bcrypt; print(bcrypt.hashpw(b'test', bcrypt.gensalt()).decode())")
    MEOWDB_PASSWORD_HASH="$HASH" MEOWDB_SESSION_SECRET="dev-secret" uv run meowdb serve

import? 'local.just'
