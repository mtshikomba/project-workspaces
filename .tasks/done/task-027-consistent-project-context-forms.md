# task-027: Keep project forms consistent across contexts

## User story

As a client, I want project create and edit forms to look and behave consistently wherever I open them, so that project management feels predictable in my personal workspace and company workspaces.

As a client creating a project from a selected workspace, I want that workspace to be selected automatically and preserved on submission, so that the project is created in the workspace I was viewing.

## Background

Projects can belong to a personal workspace or a selected company workspace. The application exposes project creation from the client overview and from inside a company workspace, while project editing can be reached from project detail contexts. These forms should share one consistent presentation and must preserve the workspace that initiated creation.

A generic project-create flow may still allow the user to choose among authorized workspaces. A selected workspace route must constrain creation to that workspace and must not silently fall back to the personal workspace or another company workspace.

## Scope

- Standardize project create and edit form structure, labels, help text, errors, actions, and navigation across personal and company-workspace contexts.
- Pass the selected workspace context into project creation routes opened from a company workspace.
- Preselect and constrain the workspace in workspace-context project creation.
- Preserve the selected workspace through valid and invalid POST responses.
- Keep the generic project-create flow available when no workspace context is supplied.
- Ensure project edit forms display the existing workspace consistently and preserve existing project values.
- Preserve workspace-specific URLs, redirects, authorization, CSRF protection, and project descriptions.

## Acceptance criteria

- [ ] Personal and company-workspace project create forms share the same visible field order, labels, required-field behavior, validation presentation, primary action, and cancel/back treatment.
- [ ] Personal and company-workspace project edit forms use the same structure and preserve the project's existing name, description, and workspace context.
- [ ] Opening project creation from a selected company workspace supplies that workspace as the form context.
- [ ] A workspace-context project form shows the originating workspace as selected and does not require the user to choose another workspace.
- [ ] A valid submission from a workspace context creates the project in the selected workspace and redirects back into that workspace context.
- [ ] An invalid submission from a workspace context re-renders with the selected workspace preserved and displays field errors without losing entered values.
- [ ] The generic project-create route continues to offer only workspaces the authenticated user may write to when no workspace context is supplied.
- [ ] A user cannot use manipulated form data or route parameters to create or edit a project in an inaccessible workspace.
- [ ] Company clients retain their existing restriction against unauthorized workspace creation or editing, while administrators retain required company-workspace controls.
- [ ] Existing project-to-task and project collaboration links continue to use the correct personal or selected workspace context after creation and editing.
- [ ] Responsive and keyboard review confirms the form is usable at desktop and 390px mobile widths without clipped fields or ambiguous actions.
- [ ] Django tests cover personal creation, company workspace-context creation, generic creation, edit consistency, invalid POST preservation, and authorization boundaries.
- [ ] `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, Black, and Flake8 pass.

## Out of scope

- Changing project fields or project membership and invitation behavior.
- Changing workspace roles, membership lifecycle, or workspace authorization rules.
- Removing the generic project-create route.
- Adding new workspace types or project-level permissions.
- Reworking project detail or task management beyond preserving their context links.

## Implementation notes

- Prefer one reusable project form/template contract with explicit context flags rather than duplicated personal and workspace implementations.
- Validate a route-supplied workspace against the existing authorized writable-workspace queryset before binding it to the form.
- Treat a selected workspace supplied by the route as authoritative; do not rely on a hidden form field for authorization.
- Preserve context-specific success and cancel URLs for personal and selected company workspace routes.
- Add GET and invalid POST regression tests to ensure the selected workspace cannot disappear during validation.

## Dependencies

- Builds on the workspace-aware project form and selected company workspace management from task-023 and task-024.
- Should align with task-026 so project and task forms use the same context-preserving conventions.

## UX handoff

The UX review should verify consistent field grouping, error placement, focus order, workspace context visibility, submit/cancel labels, and mobile behavior across personal and company workspace project forms.

## Implementation status

Implemented by `@developer`; focused and full Django test suites, Django checks, Black, Flake8, and browser validation passed.
