# Zoony Backend Agent Guide. CRITICAL RULES - MUST FOLLOW

## Stack

- Django 5.2 / DRF backend; install dependencies with `pip install -r requirements.txt` from the repo root, not pnpm.
- Runtime configuration is loaded from root `.env` by `pet_store/settings.py`; copy `.env.example` for local defaults.
- PostgreSQL is required for checks/tests that touch Django; local fallback uses `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_SSL_MODE` unless `DATABASE_URL` is set.

## Commands

- Format check: `black --check .`; auto-format with `black .`.
- Django checks: `python manage.py check`.
- Migration drift check: `python manage.py makemigrations --check --dry-run`.
- Apply migrations: `python manage.py migrate`.
- Test suite: `pytest`; pytest is configured for `pet_store.settings` and only discovers `tests_shop.py` by default.
- Focused test: `pytest shop/tests_shop.py::test_name`.
- CI order is `black --check .`, then `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --noinput`, then `pytest`.

## App Wiring

- Django project entrypoints are `manage.py`, `pet_store/settings.py`, `pet_store/urls.py`, and `pet_store/wsgi.py`.
- The main app is `shop`; models are split under `shop/models/` and re-exported from `shop/models/__init__.py` for Django/import compatibility.
- API routes are mounted at `api/` through `shop/urls.py`; auth routes are also mounted twice: `api/auth/` in `pet_store/urls.py` and `api/auth/` via `shop/urls.py`.
- `APPEND_SLASH = False`; do not add or assume trailing slashes on API paths.
- `shop.apps.ShopConfig.ready()` imports `shop.signals`; signal side effects include variant attribute synchronization and Cloudinary review-image cleanup.

## Database And Data

- For model/schema changes, create and commit Django migrations with `python manage.py makemigrations`, then verify with `python manage.py makemigrations --check --dry-run` and `python manage.py migrate`.
- Seed catalog basics with `python manage.py load_initial_data` when a local DB needs initial animals/categories/brands/attributes/badges.
- Import mock products from CSV with `python manage.py import_mockaroo_products --file MOCK_DATA.csv`; add `--replace` only when intentionally deleting prior `MOCK-` products.

## Runtime Notes

- `entrypoint.sh` requires `DATABASE_URL`, waits for PostgreSQL with SSL required, runs `migrate --noinput`, runs `collectstatic --noinput`, then starts Gunicorn on `${PORT:-8080}`.
- Local media storage is used unless AWS storage env vars are present; Cloudinary credentials are optional except for image upload paths.

## Responces
Keep responses concise and to the point - unless the user asks otherwise

## Planning mode
- Always ask clarifying questions
- Never assume design, tech stack or features
- Use deep-dive sub-agents to assist with research
- Use deep-dive sub-agents to review the different aspects of your plan before presenting to the user

## Change / Edit mode
- Never implement features yourself when possible - use sub-agents!
- Identify changes from the plan that can be implemented in parallel, and use sub-agents to implement the features efficiently
- When using sub-agents to implement features, act as a coordinator only
- Use the best model for the task - premium models for complex tasks (like coding) and mid-tier models for simpler tasks, like documentation
- After completing features (large or small), always run commands like lint, type check and next build to check code quality

## Testing
- Use any testing tools, libraries available to the project for testing your changes
- Never assume your changes simply work, always test!
- If the project does not have any testing tools, scripts, MCP tools, skills, etc. available for testing, ask the user whether testing should be skipped.


<!-- venv -->
