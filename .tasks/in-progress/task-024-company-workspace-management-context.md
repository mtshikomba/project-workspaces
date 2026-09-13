# task-024: Make company workspace the management context

## User story

As a company user, I want to enter a specific company workspace before managing its projects, tasks, members, invitations, and settings, so that every action is clearly scoped to the company I am working in.

As a client, I want `/workspace/` to remain a clean overview of only the projects and tasks linked to me, so that company administration and unrelated company work do not overwhelm my client-focused workspace.

## Background

`task-023` introduced company workspaces, memberships, invitations, workspace-aware project access, and company workspace discovery. The current landing page still mixes the personal/client overview with company workspace management entry points, and company resources are not yet organized behind a selected workspace context.

This follow-up establishes a clear navigation and authorization boundary:

- `/workspace/` is the client-linked overview.
- `/workspaces/<workspace>/` is the selected company workspace context.
- Company workspace management pages operate on the selected workspace and must not silently fall back to another workspace or the personal overview.

## Scope

- Keep `/workspace/` as the personal/client-focused landing page.
- Show on `/workspace/` only projects and tasks linked to the authenticated client, plus concise company-workspace discovery and pending invitation entry points.
- Add a company workspace entry route and navigation flow, such as `/workspaces/<int:pk>/`, for an active company membership.
- Require users to enter/select a company workspace before managing that workspace's:
  - projects;
  - tasks;
  - members and roles;
  - invitations;
  - workspace settings and other workspace-specific functionality.
- Scope all company workspace pages, forms, actions, redirects, and links to the selected workspace.
- Provide a visible way to return from a company workspace to `/workspace/`.
- Provide a workspace switcher or equivalent navigation for users who belong to multiple company workspaces and their personal workspace.
- Preserve role boundaries within the selected workspace: administrators manage workspace controls; clients can access only the company resources permitted to their role.
- Preserve direct individual-client use of `/workspace/` and personal workspace data.
- Keep non-member users from discovering or accessing another company's workspace routes or resources.

## Acceptance criteria

- [x] `/workspace/` remains a clean client-linked overview and does not expose unrelated company projects, tasks, members, invitations, or settings as if they were personal resources.
- [x] `/workspace/` lists or links to active company workspaces and pending invitations without becoming the company-management screen.
- [x] An active member can enter a selected company workspace through a stable route such as `/workspaces/<pk>/`.
- [x] The selected company workspace clearly identifies its name and current context on every workspace-scoped page.
- [x] Company workspace projects are listed and created from inside the selected company workspace.
- [x] Company workspace tasks are listed and created/updated from inside the selected company workspace.
- [x] The existing task-list/task-board component is reused in company workspace task views, including its lanes/list toggle, status controls, priority/due-date presentation, empty states, feedback region, and accessibility hooks.
- [x] The existing project-task component is reused when viewing tasks for a company workspace project, rather than introducing a parallel workspace-only task markup implementation.
- [x] Shared task components support scoped workspace URLs and status endpoints without weakening the existing personal/client overview behavior.
- [x] Company workspace members, roles, and invitations are managed from inside the selected company workspace.
- [x] Workspace settings are managed from inside the selected company workspace.
- [x] Workspace-scoped forms preserve the selected workspace and cannot be redirected to or saved against another workspace through submitted identifiers.
- [x] Workspace-scoped redirects return to the selected company workspace or the relevant workspace child page, not generically to `/workspace/` unless the action exits the context.
- [x] A user belonging to multiple company workspaces can switch between them without losing context or seeing resources from the previous workspace.
- [x] A user can return to the clean client overview from a company workspace.
- [x] A personal workspace and its projects/tasks remain available to an individual client without requiring company-workspace access.
- [x] A company client cannot access administrator-only member, invitation, or settings controls from the selected workspace.
- [x] A non-member receives a permission-denied or not-found response for another company's workspace route and cannot enumerate its resources.
- [ ] Existing project-level collaboration remains compatible where explicitly supported, but company workspace resources are governed by the selected workspace membership boundary.
- [x] Tests cover client overview isolation, workspace entry, workspace switching, scoped project/task CRUD, member/admin boundaries, redirect context, personal workspace regression, and non-member isolation.
- [x] Browser validation covers loading, empty, permission-denied, keyboard focus, mobile navigation, and multi-workspace switching states for the implemented workspace shell.
- [x] `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, Black, and Flake8 pass.

## Out of scope

- Billing, subscriptions, usage limits, or payments.
- SSO, SCIM, domain-based auto-join, or enterprise identity provisioning.
- Cross-company data sharing or a combined cross-workspace project view.
- Custom roles beyond the existing administrator and client roles.
- Replacing Django staff/superuser permissions with workspace roles.
- Real-time collaboration, chat, or notifications beyond the existing invitation lifecycle.
- Redesigning the public landing page or authentication flow.

## Implementation notes

- Introduce a reusable selected-workspace mixin/service that validates the route workspace against the authenticated user's active membership and exposes the workspace consistently to templates and forms.
- Treat the workspace route as the authorization boundary; do not rely on hidden form fields or client-submitted workspace IDs alone.
- Replace generic `client-landing` redirects in company-scoped mutations with workspace-aware success URLs.
- Separate client-linked overview querysets from workspace-scoped querysets so `/workspace/` cannot accidentally become a cross-company dashboard.
- Ensure project and task creation forms receive only the selected workspace and permitted project choices.
- Reuse `core/templates/core/_task_views.html` and the established project-detail task section for company workspace contexts; pass scoped task/status URLs and context explicitly instead of duplicating the component markup.
- Keep shared task-board JavaScript behavior identical across personal and company contexts, including status updates, lane/list switching, feedback, and empty states.
- Use `select_related`/`prefetch_related` for the workspace shell, memberships, projects, tasks, and pending invitations.
- Preserve personal-workspace compatibility for existing users and migrated projects.
- Have `@ux-developer` specify the workspace shell, switcher, breadcrumbs/back navigation, active context, loading/empty/error states, and mobile behavior before implementation.

## Dependencies and open decisions

- Recommended canonical company route: `/workspaces/<int:pk>/`; retain `/workspace/` as the personal/client overview.
- Recommended behavior: all active company members may switch between company workspaces; administrator controls remain role-gated inside each selected workspace.
- Recommended behavior: workspace invitations live in the selected workspace's Members area, while pending invitations remain discoverable from `/workspace/`.
- Confirm which workspace settings are required in the first release.
- Confirm whether `/workspace/` should show compact linked project/task counts or only navigation links to company workspaces.

## UX review handoff

Reviewed the current client landing and company member surfaces on 2026-09-13. The current implementation does not yet provide a selected-workspace context, so this ticket needs a dedicated workspace shell rather than adding more company controls to `/workspace/`.

### Information architecture

- `/workspace/`: `Client overview`. Contains only the authenticated user's linked projects/tasks, personal-workspace actions, compact company-workspace links, and pending invitation entry points.
- `/workspaces/<int:pk>/`: `Company workspace home`. Contains the selected company name, workspace switcher, workspace-scoped project/task summary, and navigation to Projects, Tasks, Members, Invitations, and Settings.
- `/workspaces/<int:pk>/projects/`: company project list and create-project entry point.
- `/workspaces/<int:pk>/tasks/`: company task list/board and create-task entry point.
- `/workspaces/<int:pk>/members/`: member list, role controls, invitations, and administrator-only actions.
- `/workspaces/<int:pk>/settings/`: workspace settings, administrator-only.

### Persistent shell

- Keep the existing `Client tasks` brand, sign-out, and profile controls.
- Add a clearly labeled workspace switcher in the company shell. The current workspace name must be visible without opening the switcher.
- Include a persistent `Client overview` link back to `/workspace/`.
- Use breadcrumbs or an equivalent context label on child pages: `Company name / Projects`, `Company name / Members`, and so on.
- Do not present company controls as part of the personal task summary.

### States to design and validate

- Loading: shell and primary content preserve stable dimensions while workspace data loads.
- Empty company workspace: explain that no projects/tasks exist yet and provide role-appropriate create actions.
- Active company workspace: show workspace name, current section, counts, and available actions.
- Multiple workspaces: switcher lists personal overview and every active company membership; the selected item is announced and visually distinct.
- Pending invitation: visible on `/workspace/`, clearly labeled as pending, with accept/decline actions; it must not appear as an active workspace until accepted.
- Permission denied: non-members see a clear denied/not-found state without workspace names, project names, or member data leaking.
- Validation/error: preserve selected workspace context, show errors next to the relevant control, and never fall back silently to `/workspace/`.
- Destructive actions: member removal, invitation revocation, and workspace settings changes require confirmation and return to the same selected workspace.

### Responsive and accessibility requirements

- Desktop: workspace switcher, section navigation, and primary action remain scannable without competing with the content area.
- Mobile: collapse navigation into an accessible control, keep the workspace name and current section visible, and make all primary actions full-width where needed.
- Keyboard: logical order is brand, workspace switcher, overview link, section navigation, page content, then secondary actions; focus must remain visible after switching or form errors.
- Every workspace-scoped page has one descriptive `h1` containing the selected workspace context and section.
- Workspace switcher uses an accessible label and exposes the selected workspace state; it must not depend on color alone.
- Empty, error, and permission-denied messages are readable by assistive technology and remain visible at mobile widths.

### UX acceptance criteria

- [ ] A browser review confirms `/workspace/` reads as a client overview and does not visually merge company administration into personal work.
- [ ] A browser review confirms the selected workspace name and current section remain visible across the workspace home, Projects, Tasks, Members, Invitations, and Settings pages.
- [ ] A browser review confirms workspace switching preserves the selected workspace in links, forms, redirects, and browser navigation.
- [ ] Desktop and 390px mobile screenshots show no horizontal overflow, clipped controls, or ambiguous active navigation.
- [ ] Keyboard review covers switcher open/close, workspace change, back navigation, form errors, and destructive-action confirmation.

## Implementation status

Implemented in the current slice:

- Selected company workspace shell at `/workspaces/<pk>/` with active-membership authorization.
- Workspace-scoped project home/list/create routes and context-preserving redirects.
- Workspace-scoped task list/create/detail/update/status/delete routes and selected-workspace project choices.
- Shared task-list/task-board reuse in workspace task lists and shared project-task sections in workspace project detail pages, with scoped detail/status URLs.
- Administrator-only workspace settings route and form.
- Client overview isolation from company projects/tasks, plus workspace switching and return navigation.
- Responsive workspace navigation, switcher, empty states, focus-visible styling, context-bearing headings, and mobile browser validation.

Remaining work:

- Complete browser validation for any future workspace child pages or settings states added beyond this slice.

## UX review

Reviewed the implemented workspace shell, client overview, project list, and empty task state at desktop and 390px mobile widths on 2026-09-13.

Passes:

- `/workspace/` reads as a client overview and shows company workspaces as entry points rather than mixing company projects into the personal task/project lists.
- The selected workspace home exposes the workspace name, switcher, client-overview link, section navigation, and role-neutral project/task entry points.
- The mobile shell and project page have no horizontal overflow, and empty project/task states are understandable.

Findings for the next implementation pass:

- **Resolved:** Added explicit `:focus-visible` treatment and context-bearing headings for workspace child pages and forms.
- **Resolved:** Added selected-workspace task detail/update/status/delete flows and administrator settings with context-preserving routes.
- **Resolved:** Workspace task lists and project detail pages now reuse `_task_views.html`, including scoped task-detail and status URLs, shared task-board JavaScript, lanes/list controls, and empty/feedback states.

## Component reuse UX review

Reviewed the workspace task list and project-task presentation on 2026-09-13. The shared `_task_views.html` component is now reused in workspace task lists and workspace project detail pages with scoped task-detail/status URLs, shared task-board JavaScript, lanes/list controls, and shared empty/feedback states. Browser validation confirmed the Lanes/List controls and no mobile horizontal overflow at 390px.
