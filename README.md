# Django Project

Minimal Django project scaffold for local development.

## Repository Instructions

`AGENTS.md` is the canonical source for repository instructions, agent responsibilities, workflow gates, ticket lifecycle rules, and the Definition of Done. `.github/copilot-instructions.md` is the sole Copilot discovery entry point and links to `AGENTS.md`; keep it as a pointer rather than maintaining a second copy of the policy. More-specific instruction files apply alongside `AGENTS.md` and take precedence when they address the same path or concern.

## Agent Workflow

This project uses four agents to move work from an idea to reviewed code:

### `@product-owner`

Turns a loose request into a groomed Markdown ticket. The ticket should include a user story, scope, acceptance criteria, out-of-scope items, and implementation notes. The product owner pauses for human approval or refinement before implementation begins.

### `@developer`

Implements an approved ticket, writes the required Django tests, and validates the change. The developer moves the ticket through the task lifecycle and prepares the feature branch and pull request.

### `@ux-developer`

Translates approved requirements into user flows, screen and component states, responsive behavior, accessible interactions, and user-facing copy. The UX developer reviews user-facing implementations in a browser at desktop and mobile widths before technical review.

### `@tech-lead`

Reviews the pull request after it is created. The review checks architecture, authorization, CSRF/XSS risks, query performance, migrations, tests, and adherence to the acceptance criteria before merge.

## End-to-End Process

1. Ask `@product-owner` to run `#groom-ticket` for the feature request.
2. Review the generated ticket and reply **Approve** or **Refine**.
3. For user-facing work, ask `@ux-developer` to define the UX specification and acceptance criteria.
4. Ask `@developer` to implement the approved ticket and UX handoff. The ticket moves from `.tasks/todo/` to `.tasks/in-progress/`.
5. The developer writes tests first where practical, implements the smallest complete change, and runs the project checks.
6. Ask `@ux-developer` to validate the implemented UI at desktop and mobile widths.
7. The developer moves the completed ticket to `.tasks/done/`, pushes the feature branch, and creates a pull request into `main`.
8. Ask `@tech-lead` to review the pull request and address any findings.
9. Merge only after UX validation, tech-lead review, and the Definition of Done checks are green.

## Task and Git Conventions

Use one task ID across the ticket, branch, and pull request:

- Tickets: `.tasks/{status}/task-NNN-{kebab-case-summary}.md`
- Lifecycle: `.tasks/todo/` -> `.tasks/in-progress/` -> `.tasks/done/`
- Branches: `task-NNN/{kebab-case-summary}`
- Pull request titles: `[task-NNN] Imperative summary`
- Pull request bodies: include the ticket ID, implementation summary, acceptance-criteria status, tests and validation, and migration notes when applicable.

Use three-digit sequential IDs that are never reused. Keep summaries concise, lowercase ASCII, and kebab-case. Preserve the same ticket filename while moving it between lifecycle folders.

Each ticket must have exactly one canonical copy. Agents must move the file rather than copy or recreate it, then verify that the source is absent and the destination exists. Before starting work, check all three lifecycle folders for duplicates; after completing work, remove any stale `todo` or `in-progress` copy so only the current status remains.

Example:

```text
Ticket: .tasks/todo/task-006-add-task-filters.md
Branch: task-006/add-task-filters
Pull request: [task-006] Add task filters
```

## Definition of Done

Before a ticket is complete:

- Django unit or integration tests pass.
- `python manage.py check` passes.
- `python manage.py makemigrations --check --dry-run` passes.
- Black formatting passes.
- Flake8 linting passes.
- New models and views have concise Google-style docstrings.
- A migration is generated and included when models change.
- Acceptance criteria are checked off in the completed ticket.
- User-facing changes pass UX validation for responsive layout, accessibility, and relevant UI states.

## Example Prompts

Groom a request:

```text
@product-owner run #groom-ticket: Add [feature description].
```

Implement an approved ticket:

```text
@developer implement task-006-add-task-filters.md.
```

Create a pull request:

```text
@developer create a PR into main for task-006.
```

Review a pull request:

```text
@tech-lead review PR #123.
```

Define UX before implementation:

```text
@ux-developer define the UX specification for task-012, including user flow, states, responsive behavior, accessibility, and browser validation.
```

Validate implemented UI:

```text
@ux-developer review the implemented UI for task-012 at desktop and mobile widths.
```

## Setup

This project targets Python 3.9 or newer within the supported Django 4.2 range.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

The settings module reads environment variables from the shell. Load `.env` with your preferred environment manager when needed; Django does not read `.env` files automatically.

### Create a local client user

Client access is granted through membership in the Django `Client` group. Create the group and assign a user with the Django shell:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Group, User

client_group, _ = Group.objects.get_or_create(name="Client")
user = User.objects.get(username="your-username")
user.groups.add(client_group)
```

Membership in `Client` is required for the client landing page; staff status alone does not grant access.

### Rich task descriptions

Task descriptions use `django-ckeditor-5` with a maintained toolbar for headings, emphasis, links, lists, block quotes, and undo/redo. `bleach` sanitizes descriptions with an allowlist before storage and again before rendering. Images and file uploads are not enabled.

### Project-first task workflow

Clients create a project before creating tasks. From the client workspace, choose **New project**, add the project name and optional description, then open the project and choose **New task**. Every task belongs to one project, and clients can only view or change projects and tasks they own.

## Run

```bash
python manage.py runserver
```

The health check is available at `http://127.0.0.1:8000/health/`.

## Docker image

The production image uses Python 3.13, Gunicorn, and the `config.wsgi:application`
WSGI entrypoint. It runs as the non-root `app` user with UID/GID `1000:1000`.
The image remains compatible with the repository's default SQLite configuration;
shared MySQL configuration is a separate deployment concern and is not added by
this image ticket.

Build and run the image locally:

```bash
docker build -t client-tasks:local .
docker run --rm --publish 8000:8000 \
	--env DJANGO_SECRET_KEY=local-container-key \
	--env DJANGO_DEBUG=true \
	--env DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost \
	--env RUN_MIGRATIONS=1 \
	client-tasks:local
```

`RUN_MIGRATIONS=1` is an explicit operator choice. Without it, the entrypoint
logs that migrations were skipped, then runs `collectstatic` and starts Gunicorn.
This avoids applying schema changes silently on every restart. For a production
deployment, run migrations as a visible release step against the selected
database before starting the web process.

The image healthcheck uses Python's standard library against `/health/`; inspect
it with `docker inspect`. Static output is written to `/app/staticfiles`, and
runtime media is expected at `/app/media`. Any mounted volume for those paths
must be writable by UID/GID `1000:1000`.

The Docker build context excludes local environment files, the development
virtual environment, SQLite data, Git metadata, test artifacts, and editor files.
Never pass `DJANGO_SECRET_KEY`, database credentials, or other secrets through
Docker build arguments; provide runtime secrets through the deployment platform.

## Docker Compose with shared MySQL

The production Compose file runs only the Django `web` service. It connects to
the existing shared MySQL instance supplied through `.env.production`; it does
not create a `db` service or a local database volume. Copy
`.env.production.example` to `.env.production` on the deployment host and fill
in real values there. Never commit that file.

The container expects `DB_ENGINE=mysql`, `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD`. Missing or incomplete MySQL settings fail startup;
the production container never silently falls back to its ephemeral SQLite
database. Use a least-privilege application account, not MySQL root. The host
must be reachable from the Docker network and allowlisted by the database
firewall; TLS requirements must follow the shared database policy. Linux Docker
does not assume that `host.docker.internal` resolves, so use the approved
private hostname or IP for `DB_HOST`.

The shared reverse-proxy network is declared as an external `proxy-tier` network
and must already exist on the host:

```bash
docker network create proxy-tier
```

Proxy routing, TLS, and labels are intentionally deferred to the reverse-proxy
deployment. The Compose file also creates an internal `app-network` for future
service connectivity. The fixed web container name is `client-tasks-web`.

Validate and start the stack after creating `.env.production`:

```bash
docker compose config
docker compose up -d --build
docker compose ps
curl --fail http://127.0.0.1:8000/health/
```

The Compose service leaves automatic migrations disabled. Run the migration as
an explicit release step with the shared database credentials before serving a
new schema:

```bash
docker compose run --rm --no-deps -e RUN_MIGRATIONS=1 web true
```

The command also runs `collectstatic` through the existing entrypoint. Static
files persist in `static_volume`, media persists in `media_volume`, and both
volumes are owned for the image's UID/GID `1000:1000` contract. Use
`docker compose down` for non-destructive teardown. Never run
`docker compose down -v` in production because it deletes the static and media
volumes.

## Test and quality checks

```bash
python manage.py test
black --check .
flake8 .
```

Use `black .` to format the project after making changes.