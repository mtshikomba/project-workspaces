# Workspaces Project

A lightweight Django app for managing projects, workspaces, and tasks for client-facing teams.

## What this project does

- Create and manage projects and workspaces
- Add tasks with rich text descriptions
- Assign tasks and manage memberships/invitations
- Keep client access limited to their own projects and tasks

## Local setup

Requires Python 3.9+ and Django 4.2.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
```

## Create a client user

Client access is granted through the Django `Client` group. You can create a user from the registration page and then assign them to the `Client` group, or create the group membership directly in Django shell.

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Group, User

client_group, _ = Group.objects.get_or_create(name="Client")
user = User.objects.get(username="your-username")
user.groups.add(client_group)
```

Membership in `Client` is required to access the client-facing pages.

## Run the app

```bash
python manage.py runserver
```

Open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health/

## Project workflow

Clients create a project first, then add tasks inside that project. Every task belongs to one project, and clients can only view or edit projects and tasks they own.

## Docker

Build and run locally:

```bash
docker build -t client-tasks:local .
docker run --rm --publish 8000:8000 \
  --env DJANGO_SECRET_KEY=local-container-key \
  --env DJANGO_DEBUG=true \
  --env DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost \
  --env RUN_MIGRATIONS=1 \
  client-tasks:local
```

The production Compose service runs Django migrations on startup with
`RUN_MIGRATIONS=1`. The application owns its MySQL schema, so sharing the
MySQL server with other applications does not share migration ownership.

## Validation

```bash
python manage.py test
python manage.py check
black --check .
flake8 .
```

Use `black .` to format the project after making changes.
