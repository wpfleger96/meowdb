# This file is managed by github-config. Do not edit manually.
# https://github.com/wpfleger96/github-config

# Settings
set dotenv-load := false

# Run quick quality checks (no tests)
default: sync type-check lint-check format-check

# Install and sync project dependencies
sync:
    uv sync

# Run mypy static type checking
type-check:
    uv run mypy .

# Check for lint issues without fixing
lint-check:
    uvx ruff check .

# Check formatting without making changes
format-check:
    uvx ruff format . --check

# Auto-fix lint issues with ruff
lint:
    uvx ruff check . --fix

# Auto-format source files with ruff
format:
    uvx ruff format .

# Sync deps then run type, lint, and format checks
check: sync type-check lint-check format-check
    @echo "Quick quality checks passed"

# Run all quality checks and tests
check-all: check test
    @echo "All quality checks and tests passed"

# Full pre-commit gate: sync, type-check, lint, format, test
pre-commit: sync type-check lint format test
    @echo "Pre-commit checks passed"

# Run all tests except e2e
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

# Build the distribution package
build: sync
    uv build

# Remove dist/, build/, and egg-info artifacts
clean-build:
    rm -rf dist/ build/ src/*.egg-info

# Clean then rebuild the distribution package
rebuild: clean-build build

# Run CI checks: sync, type-check, lint-check, format-check, test
ci: sync type-check lint-check format-check test
    @echo "CI checks passed"

# Start dev server with password auth enabled (password: test)
dev-auth:
    #!/usr/bin/env bash
    set -euo pipefail
    HASH=$(uv run python -c "import bcrypt; print(bcrypt.hashpw(b'test', bcrypt.gensalt()).decode())")
    MEOWDB_PASSWORD_HASH="$HASH" MEOWDB_SESSION_SECRET="dev-secret" uv run meowdb serve

import? 'local.just'
