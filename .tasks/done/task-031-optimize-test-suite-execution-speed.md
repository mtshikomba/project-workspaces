# task-031: Optimize test suite execution speed

## User story

As a developer on the engineering team, I want the test suite to execute in seconds rather than minutes, so that I can practice rapid test-driven development (TDD) without waiting through long test runs as the test suite grows.

As a tech lead reviewing pull requests, I want fast, reliable test execution in local development and CI pipelines, so that quality feedback is immediate and continuous integration remains lightweight.

## Background

The project test suite has grown to ~100 test cases and currently takes over 2.5 minutes (~150-160 seconds) to execute. Analysis of the test runtime indicates two primary bottlenecks:
1. **Password Hashing Overhead:** Default Django user creation in test setup uses CPU-intensive password hashers (`PBKDF2PasswordHasher` with 260,000+ iterations), causing massive slowdowns across dozens of authenticated test cases.
2. **Database Storage Configuration:** SQLite test setup creates and tears down a disk-backed test database file by default rather than using an in-memory SQLite database (`:memory:`).

Optimizing the test environment settings—such as configuring fast password hashers (`MD5PasswordHasher`) during testing and ensuring in-memory SQLite execution (`TEST: {"NAME": ":memory:"}`)—will reduce test execution times from minutes to seconds without altering any test contracts or application behavior.

## Scope

- Configure Django test settings to optimize test execution speed:
  - Override `PASSWORD_HASHERS` during testing to use `django.contrib.auth.hashers.MD5PasswordHasher` (or fast test hashers).
  - Configure the default `DATABASES["default"]["TEST"]` settings to use in-memory SQLite (`"NAME": ":memory:"`).
- Ensure settings changes apply automatically during `python manage.py test` without requiring extra command-line flags or breaking production settings.
- Verify that all 100+ existing unit, integration, view, and authorization tests continue to pass cleanly.
- Verify that test suite execution time drops dramatically (target: under 5 seconds total runtime for the full suite).
- Ensure `python manage.py check`, Black, and Flake8 pass.

## Acceptance criteria

- [x] Django test configuration uses an in-memory SQLite database (`"NAME": ":memory:"`) during test runs.
- [x] Django test configuration overrides `PASSWORD_HASHERS` during testing to use `MD5PasswordHasher` for fast user password generation.
- [x] Running `python manage.py test` executes the full test suite in under 15 seconds total runtime (compared to ~150+ seconds previously).
- [x] All 100+ existing unit, integration, workspace, project, task, and security test cases pass cleanly with zero test failures or skips.
- [x] Production database and password hashing settings in `config/settings.py` remain secure and unaffected outside of test execution.
- [x] `python manage.py check`, Black, and Flake8 pass with zero errors.

## Out of scope

- Rewriting existing test logic, assertions, or test cases.
- Changing production settings or default database configuration for `runserver` or `migrate`.
- Introducing external test runners (e.g. pytest) unless required for performance gains.
- Parallel test execution setup (`--parallel`) unless single-threaded performance needs further boost.

## Implementation notes

- In `config/settings.py`, update `DATABASES["default"]["TEST"] = {"NAME": ":memory:"}` or add a test settings module/check.
- Add `PASSWORD_HASHERS` configuration for tests in `config/settings.py` (e.g. checking if `'test' in sys.argv` or configuring `PASSWORD_HASHERS` conditionally/in test settings so `MD5PasswordHasher` is used during tests).
- Measure test execution timing before and after changes using `/Users/matheus/dev/my_crew/django-test/.venv/bin/python manage.py test`.
- Verify `python manage.py check` passes and no security features are degraded in non-test runtime environments.
