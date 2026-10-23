SHELL := /bin/bash
export PYTHONPATH := apps/api
PY := uv run

.DEFAULT_GOAL := check

.PHONY: install check lint types test eval eval-retrieval run worker up down logs migrate ingest seed fmt docs admin-dev admin-build admin-check

install:
	uv sync

check: lint types test docs

lint:
	$(PY) ruff check .

fmt:
	$(PY) ruff format .
	$(PY) ruff check . --fix

types:
	$(PY) mypy

test:
	$(PY) pytest

eval:
	$(PY) python -m onboarding.evals --write

eval-retrieval:
	$(PY) python -m onboarding.evals --retrieval-only --write

run:
	$(PY) uvicorn onboarding.api.app:create_app --factory --reload --port 8000

worker:
	$(PY) python -m onboarding.app.worker.main

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	$(PY) alembic upgrade head

ingest:
	$(PY) python -m onboarding.cli ingest

seed:
	$(PY) python -m onboarding.cli seed --file infra/demo/employees.json

docs:
	$(PY) python scripts/check_docs.py

admin-dev:
	cd apps/admin && npm run dev

admin-build:
	cd apps/admin && npm run build

admin-check:
	cd apps/admin && npm run typecheck
