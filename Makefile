SHELL := /bin/bash
export PYTHONPATH := apps/api
PY := uv run

.DEFAULT_GOAL := check

.PHONY: install check lint types test eval eval-retrieval run worker up down logs migrate ingest seed demo fmt docs admin-install admin-dev admin-build admin-check

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

cron:                              # one cron-style pass over reminders and the outbox
	PYTHONPATH=apps/api uv run python -m onboarding.app.scheduler --max-jobs 200

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

demo: ingest
	$(PY) python -m onboarding.cli demo --reset --yes

docs:
	$(PY) python scripts/check_docs.py

admin-install:
	cd apps/admin && npm ci

admin-dev:
	cd apps/admin && npm run dev

admin-build:
	cd apps/admin && npm run build

admin-check:
	cd apps/admin && npm run typecheck
