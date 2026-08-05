---
name: 'code-quality-policy'
description: 'Use when reviewing, testing, refactoring, or preparing code changes; applies project quality guidance, focused verification, generated sync checks, and risk review.'
---

# Code Quality Policy

Use this skill when reviewing, testing, refactoring, or preparing code changes.

## Priority

- Prefer project-specific `code-quality-policy` guidance and repository guidance over any shared baseline.
- Read `AGENTS.md` first.
- Check relevant README files, package scripts, CI/config files, tool configs, scripts, docs, and project-local `.agents` skills before choosing commands.
- Prefer small correct changes over broad rewrites.
- Preserve unrelated user changes and avoid formatting-only churn.

## Review Focus

- Bugs, regressions, security issues, data leaks, and secret handling.
- Maintainability, package boundaries, and dependency placement.
- Build, runtime, migration, generated-artifact, and deployment risks.
- Missing tests or missing focused verification for the changed behavior.

## Project Tooling

- Run commands from the repository root.
- Do not assume project tooling—use the commands defined in `AGENTS.md`.
- Use the project's Django tooling instead of generic examples:
  - Format check: `black --check .`
  - Auto-format: `black .`
  - Django checks: `python manage.py check`
  - Migration verification: `python manage.py makemigrations --check --dry-run`
  - Apply migrations: `python manage.py migrate`
  - Tests: `pytest` or focused `pytest shop/tests_shop.py::test_name`
- Follow the repository's CI order when performing a complete quality verification.

## Generated And Mirrored State

- Do not edit generated files or build artifacts directly unless explicitly requested.
- For Django model changes:
  - Create migrations with `python manage.py makemigrations`.
  - Verify there is no migration drift using `python manage.py makemigrations --check --dry-run`.
  - Apply migrations with `python manage.py migrate`.
- Do not manually modify migration files after they have been generated unless the user explicitly requests it.

## Verification

- Run focused verification appropriate to touched files and explain skipped checks.
- Always run the full repository formatting check with `black .` before considering code quality verification complete.
- Use `git diff --check` before committing or when preparing a final quality pass.
- If a check updates generated or formatted files, inspect the diff and rerun the relevant check.
