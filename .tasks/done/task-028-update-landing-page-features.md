# task-028: Update landing page for current features

## User story

As a prospective client, I want the landing page to explain the product's current project, task, collaboration, and company-workspace features, so that I understand what the workspace supports before I sign up.

As a returning client, I want the landing page and workspace entry actions to reflect the current product, so that I can move directly into my personal overview or a company workspace without outdated messaging.

## Background

The public landing page was written before the product gained project invitations, status-lane and list task views, company workspaces, workspace roles, workspace invitations, selected workspace management, and shared navigation. Its current copy emphasizes projects, tasks, and project collaboration but does not clearly explain the newer company collaboration model or the distinction between the client overview and selected company workspaces.

The landing experience should communicate the current product without changing authentication, workspace authorization, invitation lifecycle, or application routes. The authenticated `/workspace/` overview should remain a working client-focused entry point rather than becoming a marketing page.

## Scope

- Update the public landing page copy and feature sections to represent the current product capabilities.
- Explain the project-first task workflow, task status lanes/list view, task details, and project-level collaboration.
- Explain company workspaces, role-aware access, workspace invitations, and selected-workspace management at an appropriate high level.
- Clarify the distinction between a personal client overview and joining or entering a company workspace.
- Preserve authenticated and anonymous calls to action, including sign in, registration, and opening the workspace.
- Keep the existing visual language, design tokens, semantic structure, accessibility labels, and responsive layout patterns.
- Update landing-page tests and any user-facing copy assertions that refer to the previous feature set.

## Acceptance criteria

- [ ] Anonymous visitors can understand that the product supports personal client workspaces and company collaboration workspaces.
- [ ] The landing page clearly communicates the project-first workflow: projects contain tasks and tasks can be reviewed by status or list.
- [ ] The landing page communicates project-level client invitations and controlled collaboration without promising unrestricted access.
- [ ] The landing page communicates company workspace invitations, role-aware administration, and selected workspace management without exposing implementation-only route details.
- [ ] The page distinguishes the personal/client overview from company workspace entry in its content or calls to action.
- [ ] Anonymous users retain prominent, correctly routed Sign in and Create an account actions.
- [ ] Authenticated users retain a correctly routed Open workspace action and are not forced through registration or sign in.
- [ ] The landing page does not claim features that are not implemented, such as notifications, search, AI-agent integration, billing, or file uploads.
- [ ] Existing public landing, authentication, and workspace access behavior remains unchanged.
- [ ] The updated content is accessible with semantic headings, meaningful link text, keyboard navigation, and no information conveyed by color alone.
- [ ] UX review confirms the updated page at desktop and 390px mobile widths has no overflow, clipped copy, or unclear primary action.
- [ ] Django tests cover anonymous and authenticated landing states, required feature messaging, and all CTA destinations.
- [ ] `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, Black, and Flake8 pass.

## Out of scope

- Changing authentication, registration, logout, workspace membership, or invitation behavior.
- Changing the authenticated `/workspace/` data model or turning it into a marketing page.
- Adding new product capabilities solely to support landing-page claims.
- Adding analytics, SEO infrastructure, pricing, billing, notification, search, or AI-agent content.
- Replacing the established visual design system or introducing a separate landing-page framework.

## Implementation notes

- Treat `public_landing.html` as the primary implementation surface; update `client_landing.html` only where its entry copy or feature labels are demonstrably stale.
- Reuse existing routes and conditional authenticated/anonymous CTA behavior.
- Ground claims in the existing models and workflows: personal workspaces, company workspaces, workspace roles, invitations, project/task views, and task status controls.
- Keep content concise and scannable; do not expose internal authorization terminology where user-facing language is clearer.
- Add or update template tests for the feature claims and CTA links rather than relying only on visual review.

## Dependencies

- Reflects the capabilities delivered by task-019, task-020, task-023, task-024, and task-025.
- Coordinate with UX review before implementation because this is a user-facing content and responsive-layout change.

## UX handoff

The UX review should define the information hierarchy, exact user-facing copy, feature grouping, CTA priority for anonymous versus authenticated visitors, responsive behavior, and accessibility checks for the updated landing page.

## Implementation status

Implemented by `@developer`; full Django tests, Django checks, migration check, Black, Flake8, and browser validation passed.
