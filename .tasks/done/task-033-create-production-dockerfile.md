# task-033: Create production Dockerfile

## User story

As a developer deploying this Django application, I want a reproducible production container image so that the application can be built, started, and health-checked consistently without embedding secrets or running as root.

## Context

The repository currently runs Django 4.2.26 from the `config` project, uses `config.wsgi:application`, stores the default database in SQLite, and exposes `GET /health/` with a JSON `{"status": "ok"}` response. It has no Dockerfile, `.dockerignore`, Gunicorn dependency, static collection directory, or documented container workflow.

The supplied sister-project ticket assumes a MySQL deployment and PyMySQL. This repository does not currently configure a MySQL backend or database environment variables, so this ticket must not silently change the database engine or claim MySQL production support. The image should support the current application configuration while making the database and orchestration boundary explicit for a later deployment ticket.

## Scope

- Add a single-stage `Dockerfile` based on a pinned Python 3.13 slim image, consistent with the repository deployment decision.
- Install only the production requirements needed by the current application and Gunicorn; do not install development tooling or a future `requirements-dev.txt` file.
- Add a pinned Gunicorn dependency to `requirements.txt` and use the real WSGI path `config.wsgi:application`.
- Add a `.dockerignore` excluding `.env`, `.venv`, `db.sqlite3`, `__pycache__`, `.git`, local tooling, test artifacts, and unneeded development files.
- Create a dedicated non-root `app` user and group with fixed UID/GID `1000:1000`; ensure the application directory, static output, and documented writable runtime paths have compatible ownership.
- Add a Python-only `HEALTHCHECK` against the existing `/health/` endpoint without adding `curl`, `wget`, or `netcat` solely for health checks.
- Define and document how migrations and `collectstatic` are run. Any startup entrypoint must make migration behavior visible and must not silently apply schema changes on every restart without an explicit deployment decision.
- Preserve dependency-layer caching by copying `requirements.txt` before application source code.
- Document local build/run verification, port mapping, environment variables, health-check verification, and the expected non-root UID/GID.
- Do not pass `SECRET_KEY`, database credentials, or other secrets through Docker `ARG` or build arguments.

## Acceptance criteria

- [x] `Dockerfile` builds from the selected Python 3.13 slim base image and uses a reproducible dependency-installation layer.
- [x] The container entrypoint references `config.wsgi:application`, and a locally run container serves the Django application on port 8000.
- [x] The image does not install PostgreSQL packages, MySQL client headers, `gcc`, or `netcat-openbsd` unless a separately approved database/deployment decision requires them.
- [x] `requirements.txt` contains a pinned Gunicorn version; no unapproved database driver is added merely to support the image.
- [x] `requirements-dev.txt`, if introduced later, is not installed in the production image.
- [x] `.dockerignore` excludes `.env`, `.venv`, `db.sqlite3`, `media/` unless a later storage decision explicitly requires it, `__pycache__`, `.git`, test output, and local editor files.
- [x] The application process runs as a dedicated non-root user with documented UID/GID `1000:1000`.
- [x] The app directory and any image-local writable paths used by `collectstatic`, logs, temporary files, or the current SQLite configuration are writable by the non-root user.
- [x] The image defines a Python-only `HEALTHCHECK` for `http://127.0.0.1:8000/health/`, and the check reports healthy against a running container.
- [x] Migration and static-file behavior is explicit, documented, observable, and tested; the implementation does not unexpectedly apply migrations on every restart without operator visibility.
- [x] The Dockerfile copies `requirements.txt` before application code so an unchanged dependency manifest can reuse its installation layer.
- [x] No secret values, `.env` contents, credentials, or secret-bearing build arguments are present in the image or Docker build context.
- [x] `python manage.py check`, `python manage.py makemigrations --check --dry-run`, the full test suite, Black, and Flake8 pass for the repository state used to build the image.
- [x] Documentation includes build/run commands, health-check verification, environment configuration, migration/static-file instructions, and the expected UID/GID for volume ownership.
- [x] No database migration is introduced unless a separate approved requirement makes one necessary.

## Out of scope

- Docker Compose files, MySQL or PostgreSQL service setup, reverse proxy configuration, TLS, external volumes, and automatic deployment workflows.
- Switching the Django database backend from SQLite to MySQL or PostgreSQL.
- Adding PyMySQL, `mysqlclient`, or other database drivers without an approved database deployment ticket.
- Changing application routes, authorization behavior, page content, or domain models.
- Introducing secret values into the repository, Dockerfile, build arguments, or image layers.
- Building a complete production observability or orchestration platform.

## Implementation notes

- Verify the actual runtime Python/Django compatibility before pinning the base image; preserve the repository's current Django 4.2.26 dependency unless a separate compatibility decision is approved.
- Use `WORKDIR /app`, copy dependency manifests first, install production dependencies, then copy source with ownership set for the non-root user.
- Prefer an explicit operator-controlled migration/static-file command or a clearly logged entrypoint contract. If startup automation is chosen, document its restart semantics and failure behavior before implementation.
- Keep `/health/` and the Docker healthcheck synchronized. The endpoint currently returns a small JSON success response and does not require authentication.
- `STATIC_ROOT` is configured as `BASE_DIR / "staticfiles"` so `collectstatic` has a dedicated writable destination.
- Preserve local development behavior and do not require Docker for the existing test workflow.
- Treat any future MySQL deployment as a separate architecture decision covering database settings, driver choice, credentials, migrations, persistent storage, and readiness checks.

## Required technical review

Before implementation is approved, `@tech-lead` must review:

- Base-image and Django/Python compatibility.
- Non-root ownership for the app, SQLite database path if retained, static output, and runtime temporary paths.
- Secret exclusion from build context, layers, environment defaults, and build arguments.
- Migration and `collectstatic` execution semantics, including restart and failure behavior.
- Healthcheck reliability using only tools present in the image.
- Whether SQLite-in-container is acceptable for the intended deployment, or whether a separate database ticket must precede this work.
- Dependency-layer caching and exclusion of development dependencies.

## Approval

Status: Implemented and validated; pending technical review.

## Implementation results

- Added a single-stage `python:3.13-slim` Dockerfile with dependency-layer caching, Gunicorn, the `config.wsgi:application` entrypoint, a Python-only `/health/` healthcheck, and a non-root `app` user at UID/GID `1000:1000`.
- Added `entrypoint.sh` with visible, opt-in migrations via `RUN_MIGRATIONS=1`; normal startup skips migrations, runs `collectstatic`, and starts Gunicorn.
- Added `STATIC_ROOT = BASE_DIR / "staticfiles"`, pinned `gunicorn==23.0.0`, and added `.dockerignore` protections for secrets, local databases, virtual environments, Git metadata, and development artifacts.
- Documented image build/run commands, health verification, migration semantics, static/media paths, volume ownership, and secret handling in `README.md`.

## Validation results

- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: passed with no changes.
- Full Django test suite: 108 passed.
- `black --check core config manage.py`: passed.
- `flake8 core config manage.py`: passed.
- `docker build --tag client-tasks:task-033 .`: passed from `python:3.13-slim`.
- Container smoke test: migrations completed with `RUN_MIGRATIONS=1`, 210 static files were collected, `/health/` returned HTTP 200, Docker reported `healthy`, and the runtime identity was `uid=1000(app) gid=1000(app)`.
- Image inspection confirmed the configured non-root user and Python healthcheck; excluded `.env` and `db.sqlite3` files were absent from the running container.
