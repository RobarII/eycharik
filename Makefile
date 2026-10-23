SHELL := /bin/bash
PY := uv run

.DEFAULT_GOAL := check

.PHONY: install check lint types test eval run worker up down logs migrate ingest seed fmt docs

install:
	uv sync

check: lint types test

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
	$(PY) pytest -m eval

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

docs: check
