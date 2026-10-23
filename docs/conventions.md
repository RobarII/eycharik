# Conventions

## Language

Code, identifiers, commits, and `docs/` are English. `knowledge/`, product copy, and prompts sent
to employees are Russian. Conversation with the user follows the user.

## Code

- Python 3.12, `from __future__ import annotations` where it helps, no wildcard imports.
- `core/` imports only the standard library, `dataclasses`, `enum`, `typing`, and sibling `core/`
  modules. Importing `httpx`, `sqlalchemy`, `logging`, or `time` there is a review blocker.
- Domain values are frozen dataclasses. Public functions take and return them, not dicts.
- `NewType` for identifiers: `EmployeeId`, `RunId`, `ChunkId`, `DocId`. Never pass a bare `int`
  where an identifier is expected.
- No `Any` in public signatures; `mypy --strict` covers `core/` and `ports.py`.
- Errors are explicit classes in the module that raises them. No bare `except`. Expected refusals
  are values (`Decision`), unexpected failures are exceptions.
- No boolean flag parameters. Two functions beat one with a mode switch.
- Functions are commands or queries, not both. Early return, nesting depth at most two.
- Names come from [glossary.md](glossary.md). `utils`, `helpers`, `common`, `manager`, `data`,
  `info`, `process` are forbidden module and function names.

## Tests

- Unit tests cover `core/` with no I/O and no patching. Fakes for ports live in `tests/fakes.py`
  and are five lines each, not mocks.
- Integration tests run against Postgres in docker and are marked `@pytest.mark.integration`.
- Eval tests are marked `@pytest.mark.eval` and never run in `make check`.
- Test names state behaviour: `test_escalates_when_answer_has_no_supported_citation`.
- No `sleep`, no wall-clock dependency, no network.

## Database

- SQLAlchemy 2 style, typed models, Alembic migrations, forward only.
- Every table has `created_at`; mutable tables have `updated_at`.
- Money and cost are `numeric`, never `float`.
- Identifiers are UUIDv7 in application code, not database defaults.

## Commits

Conventional Commits, English, header only, at most 72 characters.

`type(scope): subject`, scope is `api`, `admin`, `docs`, `infra`, `eval`, `kb`.

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`.

## Documentation

- Every doc is listed in [README.md](README.md).
- Headings are stable: they are link targets and eval references.
- Numbers require command, environment, and commit in `measurements/`.
- A decision that reverses an accepted ADR is a new ADR with `supersedes:`.
