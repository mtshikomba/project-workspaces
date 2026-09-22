# task-034: Create production Docker Compose configuration

## User story

As a developer deploying this Django application, I want a production `docker-compose.yml` for the web service so that the Dockerfile can run against the existing shared MySQL database without creating a second database instance or risking data loss during container replacement.

## Relationship to other tickets

This ticket builds on task-033, which provides the production Dockerfile, Gunicorn entrypoint, static collection behavior, and container healthcheck. It adapts the sister-project Compose design to this repository's architecture: the application shares an already-managed MySQL database, so this Compose file must not define a `db` service or a local MySQL data volume.

The current repository defaults to SQLite and does not yet read MySQL connection variables. Task-033 must either be completed with the agreed production configuration boundary or this ticket must include the minimal settings/dependency changes required to select MySQL when production variables are present. Local development and tests must continue to use SQLite unless explicitly configured otherwise.

## Problem

The sister-project Compose draft defines an in-Compose MySQL service and persistent database volume. That is incorrect for this project because the production database already exists outside this Compose project and is shared by multiple applications. Starting another MySQL instance would create the wrong data boundary, while allowing the container to fall back silently to SQLite would store production data inside the ephemeral web container.

The Compose definition also needs an explicit production environment file, static/media volume paths matching the Dockerfile/settings contract, a reachable external database host, safe restart behavior, and clear operator instructions. It must not embed credentials or assume that Linux containers can reach a host database through Docker Desktop-only names.

## Scope

- Add a production-oriented `docker-compose.yml` using the existing Dockerfile to run only the Django `web` service.
- Do not define a `db` service, `mysql_data` volume, database initialization command, or database backup behavior.
- Add named `static_volume` and `media_volume` mounts at the paths defined by the production settings, expected to be `/app/staticfiles` and `/app/media` respectively.
- Add an `env_file: .env.production` reference for the container's non-secret and secret runtime configuration. The file must remain VM-local and uncommitted.
- Document required application variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`, or the exact names selected by the production settings implementation.
- Ensure production settings select the shared MySQL backend when the production database variables are present and never silently fall back to SQLite in the production Compose workflow.
- Add the pinned pure-Python MySQL driver required by the selected Django backend, unless task-033 or an approved existing dependency already supplies it.
- Attach `web` to a dedicated application network for future service-level connectivity and, only where the deployment architecture already provisions it, an externally managed shared reverse-proxy network such as `proxy-tier`. Do not create or manage an external network from Compose.
- Defer proxy technology, routing labels, TLS, and certificate management to the reverse-proxy deployment ticket; network attachment alone must not be described as publishing the application.
- Use a restart policy appropriate for a long-running web service and document its operational effect.
- Add `.env.production` explicitly to `.gitignore` and add a non-secret `.env.production.example` containing variable names and safe placeholders only.
- Document that `docker compose down -v` must never be used against production because it destroys named static/media volumes, even though the database is external.
- Document external MySQL prerequisites: network reachability from the container, firewall allowlisting, TLS requirements if applicable, least-privilege credentials, schema ownership/migration responsibility, and the fact that `host.docker.internal` is not assumed to resolve on Linux.
- Reuse the Dockerfile entrypoint and healthcheck rather than duplicating startup logic in Compose.

## Acceptance criteria

- [x] `docker-compose.yml` uses the current Compose Specification without an obsolete top-level `version` key and passes `docker compose config` with no configuration warnings.
- [x] The `web` service builds from the approved task-033 Dockerfile and uses the real WSGI application path `config.wsgi:application` through that image.
- [x] No `db` service, `mysql_data` volume, database initialization container, or database credentials hardcoded in Compose are present.
- [x] `static_volume` mounts at the configured `STATIC_ROOT` path and `media_volume` mounts at the configured `MEDIA_ROOT` path; the paths are verified against the settings and Dockerfile entrypoint.
- [x] The web container reads all production settings and shared-MySQL connection values from `.env.production`; no secret is committed or passed through a build argument.
- [x] `.env.production` is explicitly ignored and `.env.production.example` documents every required variable without real secrets.
- [x] Production settings use MySQL when `DB_HOST` or the selected production database switch is present and fail clearly when required database variables are missing; they do not silently use container-local SQLite for production.
- [x] The selected MySQL driver and version are pinned in `requirements.txt`.
- [x] The Compose service joins the required application network and the externally managed proxy network without attempting to create the external network.
- [x] No proxy labels, `VIRTUAL_HOST` variables, TLS configuration, or claims of reverse-proxy reachability are added unless approved by the separate proxy deployment ticket.
- [x] `docker compose up -d --build` starts the web service with migrations disabled by default, `collectstatic` logged, and the application responding on the exposed port.
- [ ] External MySQL connectivity and migration execution are validated against the real shared instance; this requires the deployment host, credentials, firewall, and TLS configuration.
- [x] Restart behavior is documented and does not destroy the external database or named static/media volumes.
- [x] `docker compose down` is documented for non-destructive teardown, and the documentation explicitly forbids `docker compose down -v` in production.
- [x] `python manage.py check`, `python manage.py makemigrations --check --dry-run`, the full test suite, Black, Flake8, `docker compose config`, and a local web-service Compose smoke test pass.
- [x] No migration is added; production database migrations remain an explicit deployment step.

## Out of scope

- Defining or running a MySQL container, MySQL data volume, backup/restore process, retention policy, or database provisioning workflow.
- Creating or managing the shared MySQL instance, database/schema, users, firewall rules, private networking, or TLS certificates.
- Implementing the reverse-proxy service, routing rules, labels, TLS termination, certificate renewal, or public DNS.
- Automatic deployment from `main` or VM provisioning.
- Changing application page content, authorization rules, or unrelated domain behavior.
- Committing `.env.production`, credentials, database dumps, or any other secret material.

## Implementation notes

- Complete or explicitly coordinate with task-033 before implementation; the Compose file cannot be validated against MySQL until the image has the required driver, production settings, static root, and healthcheck.
- Prefer a stable external hostname or private IP for `DB_HOST` supplied through `.env.production`. Do not use `host.docker.internal` unless the target Linux Docker Engine is explicitly configured to provide it and that decision is documented.
- Use the least-privilege shared MySQL application account, never the MySQL root account. The database owner must define schema migration ownership and deployment ordering before enabling automatic migrations.
- Keep the external database off the proxy network. Only the web service should join the proxy network, if that network is already provisioned for this deployment.
- Keep static and media volume ownership compatible with the task-033 non-root UID/GID `1000:1000`; document the operator steps for preparing or repairing volume permissions.
- Do not use Compose variable interpolation for secrets when an explicit `env_file` contract is intended; distinguish Compose-time variables from variables injected into the container.
- Treat missing external database connectivity as a startup failure, not as a reason to revert to SQLite.

## Required technical review

Before implementation is approved, `@tech-lead` must review:

- The external-MySQL architecture and proof that no second database instance or data volume is created.
- Production settings selection and the fail-closed behavior when database variables are missing.
- MySQL driver compatibility with the pinned Django/Python versions and the shared server version.
- Secret handling in Compose, `.env.production`, image layers, logs, and healthchecks.
- Network reachability, Linux host-name assumptions, firewall/TLS requirements, and least-privilege database credentials.
- Migration ownership and restart behavior for a shared database used by multiple applications.
- Static/media volume ownership for the task-033 non-root container user.
- Separation between application network attachment and future reverse-proxy routing.

## Definition of done

- The Compose file runs the Django web service from the approved image against the existing shared MySQL database.
- Static and media data persist through web-container recreation without introducing a local database volume.
- No secrets are committed, and production configuration fails clearly when required values are missing.
- The ticket is moved from `.tasks/todo/` to `.tasks/in-progress/` only when implementation begins, then to `.tasks/done/` after successful Compose and shared-MySQL validation.

## Approval

Status: Implemented; awaiting shared-MySQL validation on the deployment host.

## Implementation results

- Added `docker-compose.yml` with only the Django `web` service, `static_volume`, `media_volume`, internal `app-network`, and externally managed `proxy-tier`.
- Added `.env.production.example` and explicitly ignored `.env.production`; no production environment file or credentials were committed.
- Added environment-driven MySQL settings with PyMySQL `1.1.1`. SQLite remains the local/test default, while `DB_ENGINE=mysql` or `DB_HOST` requires all database settings and fails closed when incomplete.
- Added `CSRF_TRUSTED_ORIGINS` environment parsing and production secret validation when `DJANGO_DEBUG=false`.
- Documented shared database prerequisites, Linux hostname behavior, least-privilege credentials, explicit migrations, volume ownership, proxy boundaries, and safe teardown.

## Validation results

- Django checks, migration drift check, and the full 108-test suite passed.
- Black and Flake8 passed for project source.
- `docker compose config --quiet` passed.
- Fail-closed settings check passed: incomplete MySQL configuration raised a clear missing-settings error; complete placeholder configuration passed Django checks.
- The rebuilt image included PyMySQL and reused the task-033 dependency layer during Compose build.
- Local Compose smoke test passed for the web layer: 210 static files collected, `/health/` returned HTTP 200, and the container ran as UID/GID `1000:1000`.
- Real shared-MySQL connectivity and migration validation remain pending because no shared database endpoint or credentials are available in this workspace.
