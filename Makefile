SHELL := /bin/bash
export PYTHONPATH := apps/api
PY := uv run

.DEFAULT_GOAL := check

.PHONY: install check verify verify-demo review doctor demo demo-live demo-data demo-data-del nuke lint types arch test test-cov test-integration eval eval-retrieval eval-ocr eval-sentiment eval-lint eval-baseline eval-acl run worker up down logs migrate ingest seed fmt docs docs-index diagram admin-install admin-dev admin-build admin-check admin-e2e admin-e2e-stack security prod-config prod-up smoke deploy-remote backup restore

COVERAGE_MIN ?= 85

install:
	uv sync
	cd apps/admin && npm ci

check: lint types arch test docs admin-check

doctor:                            # read-only preflight: tools, ports, state
	./scripts/doctor.sh

security:                          # supply chain: python, npm, workflows, shell, dockerfiles, secrets
	$(PY) --with pip-audit pip-audit --skip-editable
	cd apps/admin && npm audit --omit=dev --audit-level=high
	docker run --rm -v "$$PWD:/repo" -w /repo rhysd/actionlint:1.7.7
	docker run --rm -v "$$PWD:/mnt" -w /mnt --entrypoint shellcheck \
		koalaman/shellcheck:v0.10.0 --severity=warning scripts/*.sh
	docker run --rm -v "$$PWD:/mnt" -w /mnt hadolint/hadolint:v2.12.0 \
		hadolint Dockerfile apps/admin/Dockerfile
	docker run --rm -v "$$PWD:/repo" -w /repo zricethezav/gitleaks:v8.28.0 \
		detect --redact --no-banner

verify:                            # the gate: what CI runs, in one command
	@test -n "$$ONBOARDING_TEST_DATABASE" || { \
		echo "ONBOARDING_TEST_DATABASE is required: it names a separate database, not the demo one" >&2; \
		echo "hint:" >&2; \
		echo "  docker compose up -d postgres" >&2; \
		echo "  docker compose exec -T postgres createdb -U onboarding onboarding_test" >&2; \
		echo "  DATABASE_URL=postgresql+asyncpg://onboarding:onboarding@localhost:55432/onboarding_test uv run alembic upgrade head" >&2; \
		echo "  export ONBOARDING_TEST_DATABASE=postgresql+asyncpg://onboarding:onboarding@localhost:55432/onboarding_test" >&2; \
		exit 2; \
	}
	$(PY) ruff check .
	$(PY) mypy
	$(PY) lint-imports
	$(PY) python scripts/docs_index.py --check
	$(PY) python scripts/check_docs.py
	$(PY) pytest -m "not eval" --cov=onboarding --cov-fail-under=$(COVERAGE_MIN)
	cd apps/admin && npm run lint && npm run typecheck && npm run test

verify-demo:                       # end-to-end proof: stack, seed, admin API numbers
	./scripts/verify_demo.sh

review:                            # one reviewer path: preflight, stack, seed, counters
	./scripts/doctor.sh
	./scripts/verify_demo.sh

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

test-cov:                          # offline + postgres, one number, fails below the floor
	@test -n "$$ONBOARDING_TEST_DATABASE" || { \
		echo "ONBOARDING_TEST_DATABASE is required: start postgres and run the migrations" >&2; \
		exit 2; \
	}
	$(PY) pytest -m "not eval" --cov=onboarding --cov-fail-under=$(COVERAGE_MIN)

test-integration:                  # postgres only; skipped silently when the URL is absent
	$(PY) pytest -m integration

# Live tier: real Postgres and real providers. Costs money and needs keys, so it never runs in check.
test-live:
	$(PY) pytest -m "integration or eval"

eval:
	$(PY) python -m onboarding.evals --write $(ARGS)

eval-retrieval:
	$(PY) python -m onboarding.evals --retrieval-only --write $(ARGS)

eval-acl:                           # every (viewer, document) pair; no provider key, no generation
	$(PY) python -m onboarding.evals.acl --write $(ARGS)

eval-lint:                          # the set matches its contract and every gate has a mutant
	$(PY) pytest apps/api/tests/test_golden.py apps/api/tests/test_eval_gates_have_power.py apps/api/tests/test_eval_stats.py

eval-baseline:                      # pin this run: gate = Wilson lower bound of what it measured
	$(PY) python -m onboarding.evals --write-baseline --write $(ARGS)

eval-ocr:                          # extraction quality; needs no database and no provider key
	$(PY) python -m onboarding.evals.ocr $(ARGS)

eval-sentiment:                     # PROVIDER=keyword|prompt|decisions, SPLIT=dev|test|all
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

prod-config:                       # validate the prod override without a real .env.prod
	docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod config -q

prod-up:                           # production compose on the VM; needs .env.prod and TAG
	docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d

smoke:                             # public smoke test; BASE_URL overrides the default host
	./scripts/smoke.sh

deploy-remote:                     # on the VM: SHA=<commit> make deploy-remote
	@test -n "$(SHA)" || { echo "SHA is required" >&2; exit 2; }
	./scripts/deploy-remote.sh "$(SHA)"

backup:                            # consistent dump; BACKUP_S3_URI enables offsite upload
	./scripts/backup.sh

restore:                           # destructive: CONFIRM_RESTORE=yes FILE=<dump> make restore
	@test -n "$(FILE)" || { echo "FILE is required" >&2; exit 2; }
	CONFIRM_RESTORE=yes ./scripts/restore.sh "$(FILE)"

migrate:
	$(PY) alembic upgrade head

ingest:
	$(PY) python -m onboarding.cli ingest

seed:
	$(PY) python -m onboarding.cli seed --file infra/demo/employees.json

demo-data:
	docker compose run --rm api python -m onboarding.cli ingest
	docker compose run --rm api python -m onboarding.cli demo --reset --yes

demo:                              # compose up, seed, print the door and the token
	docker compose up -d --build
	$(MAKE) --no-print-directory demo-data
	@echo "open http://localhost:3000 and enter dev-hr-token"

demo-live:                         # the same, with real models from .env.live (free tier works)
	@test -f .env.live || { echo "cp .env.live.example .env.live and set LLM_API_KEY" >&2; exit 2; }
	docker compose --env-file .env.live up -d --build
	$(MAKE) --no-print-directory demo-data
	@echo "open http://localhost:3000 and enter dev-hr-token"

nuke:                              # destructive: drops the compose volume and the demo database
	docker compose down -v --remove-orphans
	-docker rm -f onboarding-pg
	@echo "nuke: compose volume, containers and the local demo postgres are gone"

demo-data-del:
	docker compose up -d postgres
	docker compose exec -T postgres psql -U onboarding -d onboarding -v ON_ERROR_STOP=1 < scripts/demo-data-del.sql

diagram:                           # render the slide-shaped end-to-end SVG
	$(PY) python scripts/diagram_end_to_end.py

docs:
	$(PY) python scripts/docs_index.py --check
	$(PY) python scripts/check_docs.py

docs-index:
	$(PY) python scripts/docs_index.py --write

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

admin-e2e:                         # the fixture: an in-memory api, no database
	cd apps/admin && npm run e2e

admin-e2e-stack:                   # the real cabinet: nginx, api, postgres; needs a running stack
	cd apps/admin && E2E_BASE_URL=$${E2E_BASE_URL:-http://127.0.0.1:3000} npm run e2e:stack
