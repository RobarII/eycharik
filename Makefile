SHELL := /bin/bash
export PYTHONPATH := apps/api
PY := uv run

.DEFAULT_GOAL := check

.PHONY: install check lint types arch test eval eval-retrieval eval-ocr eval-sentiment eval-lint eval-baseline run worker up down logs migrate ingest seed demo fmt docs admin-install admin-dev admin-build admin-check admin-e2e

install:
	uv sync
	cd apps/admin && npm ci

check: lint types arch test docs admin-check

lint:
	$(PY) ruff check .

fmt:
	$(PY) ruff format .
	$(PY) ruff check . --fix

types:
	$(PY) mypy

arch:                              # import cycles, layer order, and "api never calls a model"
	$(PY) lint-imports

test:
	$(PY) pytest

# Live tier: real Postgres and real providers. Costs money and needs keys, so it never runs in check.
test-live:
	$(PY) pytest -m "integration or eval"

eval:
	$(PY) python -m onboarding.evals --write

eval-retrieval:
	$(PY) python -m onboarding.evals --retrieval-only --write

eval-lint:                          # the set matches its contract and every gate has a mutant
	$(PY) pytest apps/api/tests/test_golden.py apps/api/tests/test_eval_gates_have_power.py apps/api/tests/test_eval_stats.py

eval-baseline:                      # pin this run: gate = Wilson lower bound of what it measured
	$(PY) python -m onboarding.evals --write-baseline --write

eval-ocr:                          # extraction quality; needs no database and no provider key
	$(PY) python -m onboarding.evals.ocr $(ARGS)

eval-sentiment:                     # PROVIDER=keyword|prompt|jev, SPLIT=dev|test|all
	$(PY) python -m onboarding.evals.sentiment --provider $(or $(PROVIDER),prompt) --split $(or $(SPLIT),all) --repeat $(or $(REPEAT),1) $(ARGS) --write

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
	cd apps/admin && npm run lint
	cd apps/admin && npm run typecheck
	cd apps/admin && npm run test

admin-e2e:
	cd apps/admin && npm run e2e
