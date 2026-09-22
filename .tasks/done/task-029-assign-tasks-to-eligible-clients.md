# task-029: Assign tasks to eligible workspace or project clients

## User story

As a project owner or workspace collaborator, I want to assign a task to a specific client who has accepted membership in the project or workspace, so that team members can clearly track task ownership and responsibilities.

As a client or workspace member, I want to see which tasks are assigned to me or other eligible collaborators, so that I can easily focus on my assigned work.

## Background

Currently, tasks in the system are associated with a owning client (`client`) and a project (`project`), but there is no concept of an assigned worker/collaborator on individual task items (`assigned_to`). Collaborators who have accepted project invitations (`ProjectMembership`) or workspace invitations (`WorkspaceMembership`) can view and manage tasks in shared projects/workspaces, but cannot assign tasks to specific members.

Adding task assignment requires enforcing strict authorization boundaries: a task can only be assigned to users who have explicitly accepted membership in the task's project or workspace (or the project owner). Uninvited users, users with pending/declined/revoked invitations, or users outside the project/workspace must never be assignable.

## Scope

- Extend the `Task` model with an optional `assigned_to` field referencing `User`.
- Define assignment eligibility rules:
  - The project owner (`project.client`).
  - Active project members (`ProjectMembership` with `is_active=True`).
  - Active workspace members (`WorkspaceMembership` with `is_active=True`) if the project belongs to a workspace.
- Enforce that pending, declined, or revoked invitees cannot be assigned to tasks until they explicitly accept an invitation.
- Update task creation and update forms (`TaskForm` and any workspace-scoped task forms) to include the `assigned_to` field, dynamically populating/filtering the field queryset to eligible users only.
- Validate assignment choices in form processing and service logic (`clean_assigned_to` / validation helpers) to reject ineligible user assignments.
- Display task assignment across task detail pages, task board lanes, task list items, and workspace task views (including clear "Unassigned" indicators when no user is assigned).
- Support setting, changing, and clearing task assignments for users with task edit permissions.
- Maintain existing workspace and project tenant isolation boundaries.

## Acceptance criteria

- [x] `Task` model includes an optional `assigned_to` field (`ForeignKey` to `User`, `on_delete=models.SET_NULL`, `null=True`, `blank=True`, `db_index=True`, `related_name="assigned_tasks"`).
- [x] Database migration is generated and `python manage.py makemigrations --check --dry-run` passes.
- [x] Task creation and edit forms expose an `assigned_to` field containing only eligible clients for the selected/context project.
- [x] The project owner (`project.client`) is always included in the eligible client choices.
- [x] Users with active `ProjectMembership` on the task's project are included in the eligible client choices.
- [x] If the task's project belongs to a workspace, users with active `WorkspaceMembership` on that workspace are included in the eligible client choices.
- [x] Users who have pending, declined, or revoked invitations (workspace or project) and do not have an active membership are strictly excluded from assignment choices.
- [x] Form submission validates that `assigned_to` is an eligible client; selecting an ineligible user raises a clear form validation error.
- [x] An authorized user can assign a task during task creation and update an existing task's assignment.
- [x] An authorized user can clear a task assignment (set to `assigned_to=None`).
- [x] Task detail views, task list items, task board cards/lanes, and workspace task views display the assigned client (or a clear "Unassigned" status badge when unassigned).
- [x] If a user's membership is removed or deactivated, existing assigned tasks retain data integrity (`on_delete=models.SET_NULL`), and forms prevent re-assigning or submitting ineligible users.
- [x] Unit and integration tests cover task assignment eligibility filtering, form validation, assignment persistence, clearance, and tenant isolation.
- [x] `python manage.py test`, `python manage.py check`, Black, and Flake8 pass.
- [x] Keyboard navigation and UI acceptance criteria are validated at desktop and mobile screen widths.

## UX Specification

### Primary User Flows
1. **Assigning during creation/editing:**
   - Navigating to task creation or edit form renders an "Assigned client" field (dropdown `<select>`).
   - Default choice for optional assignment is "Unassigned" (`""`).
   - Dropdown options display eligible user usernames (e.g. `alex (Project owner)`, `sam`, `taylor`).
   - Selecting a client and submitting saves the assignment.

2. **Viewing assigned task:**
   - On **Task Detail**: Displays an "Assigned client" entry in the detail grid with username badge or "Unassigned" label.
   - On **Task Board Cards (Lanes view)**: Renders assignee metadata badge alongside priority and due date.
   - On **Task Table (List view)**: Displays an "Assignee" column with assigned username or "Unassigned" placeholder.

### Interface & Component States
- **Form Select Control:**
  - Label: `Assigned client`
  - Help text: `Select a client who belongs to this project or workspace.`
  - Default option: `---------` or `Unassigned`
  - Disabled state: When editing in restricted view or if user lacks permissions.
  - Error state: Displays inline field validation error (e.g., `Select a valid choice. That user is not an active member of this project or workspace.`).
- **Status Badges & Labels:**
  - Assigned: `<span class="assignee-badge">@username</span>`
  - Unassigned: `<span class="assignee-badge assignee-badge--unassigned">Unassigned</span>`

### Responsive & Accessibility Requirements
- **Desktop (>=1024px):**
  - Form select input aligns cleanly within `login-panel task-form-panel`.
  - Task List Table includes "Assignee" header column between "Task" and "Status" or "Due", avoiding horizontal overflow.
  - Task Board Cards display metadata cleanly without truncation clipping.
- **Mobile (<768px):**
  - Select dropdown expands to 100% width with 44px touch target height.
  - Task Board cards stack assignee badge below task title/priority.
  - Task Table wraps or truncates metadata cleanly without breaking table bounds.
- **Keyboard & Screen Reader:**
  - Standard form control focus rings (`:focus-visible`).
  - Screen reader friendly `<label>` associations for `assigned_to` input.
  - Proper ARIA attributes for task view panels and select dropdowns.

## Out of scope

- Automated task assignment notifications or email alerts.
- Multi-user assignment (assigning multiple users to a single task).
- Workload capacity planning, time tracking, or assignment analytics.
- Self-assignment permissions distinct from existing task edit permissions.
- Assignment rules based on external roles or non-member users.

## Implementation notes

- Add `assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks", verbose_name="assigned client", help_text="The client user assigned to perform this task.", db_index=True)` to `Task` in `core/models.py`.
- Create a helper service function (e.g. `get_eligible_task_assignees(project)`) in `core/services.py` that queries and returns a `User` queryset containing `project.client`, active `ProjectMembership` users, and (if `project.workspace`) active `WorkspaceMembership` users.
- Update `TaskForm` in `core/forms.py` to include `assigned_to` in `fields`, populate its `queryset` using the eligible assignees helper based on project context, and add validation in `clean_assigned_to()`.
- Update templates (`_task_views.html`, `task_detail.html`, `task_form.html`, `workspace_task_detail.html`, `workspace_task_form.html`, etc.) to display the assigned user label/badge and provide an intuitive select control in forms.
- Ensure `select_related("assigned_to")` is added to task list and detail querysets in `core/views.py` to avoid N+1 query overhead.
- Coordinate with `@ux-developer` to review responsive layouts and form rendering for task assignment at desktop and mobile widths.
