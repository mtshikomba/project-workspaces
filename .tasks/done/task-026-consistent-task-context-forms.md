# task-026: Keep task forms consistent across contexts

## User story

As a client, I want task create and edit forms to look and behave consistently wherever I open them, so that I can update work without re-learning the form or losing the project context I started from.

As a client creating a task from a specific project, I want that project to be selected automatically and preserved on submission, so that the task is created in the project I was viewing.

## Background

The application supports personal and company-workspace task flows, including task creation from a project detail page and from broader task/workspace views. The task form should use one consistent interaction pattern across these contexts. When the form is opened from a project-specific route, the project relationship is already known and should not require the user to select it again or risk assigning the task to another accessible project.

The generic task-create route must remain available for contexts where no project has been selected. Existing task authorization, project access, workspace scoping, and project-first behavior remain authoritative.

## Scope

- Standardize the task create and edit form structure, labels, help text, errors, actions, and navigation across personal and company-workspace contexts.
- Pass the originating project context into task creation routes opened from a project detail page.
- Preselect the originating project in the task form and prevent accidental reassignment when the project is fixed by the route context.
- Preserve the selected project through valid and invalid POST responses.
- Keep the generic task-create flow available when no project context is supplied.
- Ensure edit forms display the task's existing project consistently and enforce the existing edit authorization.
- Preserve workspace-scoped URLs, redirects, status controls, descriptions, priority, due date, and all existing form fields.

## Acceptance criteria

- [ ] Personal and company-workspace task create forms share the same visible field order, labels, required-field behavior, validation presentation, primary action, and cancel/back treatment.
- [ ] Personal and company-workspace task edit forms use the same structure and preserve the task's existing values, including project, status, priority, due date, and description.
- [ ] Opening task creation from a project detail page supplies that project as the form context.
- [ ] A project-context task form shows the originating project as selected and does not require the user to choose another project.
- [ ] A valid submission from a project context creates the task under the originating project and redirects within the same personal or selected company workspace context.
- [ ] An invalid submission from a project context re-renders with the originating project preserved and displays field errors without losing entered values.
- [ ] The generic task-create route continues to allow selection from only the authenticated user's accessible projects when no project context is supplied.
- [ ] A user cannot use manipulated form data or route parameters to create or edit a task in an inaccessible project or workspace.
- [ ] Existing task update endpoints, CSRF protection, and authorization tests remain passing.
- [ ] Responsive and keyboard review confirms the form is usable at desktop and 390px mobile widths without clipped fields or ambiguous actions.
- [ ] Django tests cover personal project-context create, company project-context create, generic create, edit consistency, invalid POST preservation, and authorization boundaries.
- [ ] `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, Black, and Flake8 pass.

## Out of scope

- Changing task fields, statuses, priorities, descriptions, or due-date semantics.
- Changing project membership, workspace membership, or authorization rules.
- Removing the generic task-create route.
- Introducing a separate form implementation for every workspace type.
- Adding new task workflow features unrelated to context preservation.

## Implementation notes

- Prefer one reusable form/template contract with explicit context flags rather than duplicating personal and workspace forms.
- Validate the originating project against the view's existing authorized queryset before binding it to the form.
- Treat a project supplied by the route as authoritative; do not trust a hidden field alone to enforce ownership or workspace access.
- Preserve context-specific success and cancel URLs for personal and selected company workspace routes.
- Add regression tests for both GET rendering and invalid POST rendering so context loss cannot reappear.

## Dependencies

- Builds on the project-first task workflow from task-007 and project preselection work from task-021.
- Must remain compatible with selected company workspace management from task-024.

## UX handoff

The UX review should verify consistent field grouping, error placement, focus order, project context visibility, submit/cancel labels, loading or validation states, and mobile behavior across personal and company workspace task forms.

## Implementation status

Implemented by `@developer`; focused and full Django test suites, Django checks, Black, Flake8, and browser validation passed.
