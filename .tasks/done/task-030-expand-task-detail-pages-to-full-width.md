# task-030: Expand task detail pages to full workspace width

## User story

As a client or workspace collaborator, I want the task detail page to use the full workspace content width across personal and company workspace contexts, so that task details, descriptions, metadata, and action controls are consistent with other workspace views and easier to read.

As a team member reviewing task requirements, I want rich-text task descriptions and metadata grids to layout cleanly on wider displays, so that reading and navigating task details feels natural and unconstrained.

## Background

Currently, personal task detail pages (`/tasks/<id>/`) and company workspace task detail pages (`/workspaces/<ws_id>/tasks/<task_id>/`) use `.detail-panel`, which caps content width at 760px. In contrast, project pages (`task-013`), workspace dashboards, and task board/list views utilize the full width of `.page-shell`.

This width restriction creates visual inconsistency when transitioning between project/workspace task lists and task detail pages. Expanding task detail pages to use the full workspace shell width brings visual alignment, improves readability for rich-text task descriptions, and makes task detail views consistent across all contexts.

## Scope

- Expand task detail pages in both personal client overview (`/tasks/<id>/`) and company workspace (`/workspaces/<ws_id>/tasks/<task_id>/`) contexts to use the available desktop `page-shell` width.
- Preserve existing typography, visual hierarchy, back-link navigation, eyebrow titles, rich-text description styling, metadata grid items (Assigned Client, Status, Priority, Project, Due Date, Last Updated), and action buttons.
- Ensure the detail grid and rich-text description containers adapt smoothly across desktop (≥1024px), tablet, and mobile (<768px) viewports without awkward whitespace or text truncation.
- Verify full keyboard accessibility, focus management, and responsive layout behavior.
- Maintain existing authorization boundaries and URL routes.

## Acceptance criteria

- [x] Personal task detail page (`/tasks/<id>/`) uses the available desktop content width of `page-shell` instead of being capped at a narrow 760px column.
- [x] Company workspace task detail page (`/workspaces/<ws_id>/tasks/<task_id>/`) uses the same full-width layout treatment.
- [x] Task detail pages remain visually consistent with the rest of the client workspace layout (header alignment, spacing, typography, back links, eyebrow, metadata grid, and action buttons).
- [x] Rich-text task descriptions expand cleanly across desktop widths while maintaining readable typography and line height.
- [x] The detail metadata grid (Assigned Client, Status, Priority, Project, Due Date, Last Updated) wraps and aligns cleanly across mobile, tablet, and desktop viewports.
- [x] Tasks with and without descriptions, due dates, project assignments, or task assignees render correctly with no layout shift or visual breakage.
- [x] At mobile screen widths (<768px), task detail pages stack metadata cleanly with touch-friendly action buttons and zero horizontal page overflow.
- [x] Existing task actions (Edit task, Delete task, Back to workspace/tasks) remain fully functional.
- [x] Unit and view tests verify layout structure and content presentation for task detail views in both personal and workspace contexts.
- [x] `python manage.py test`, `python manage.py check`, Black, and Flake8 pass cleanly.
- [x] Keyboard navigation and UI acceptance criteria are validated in the browser at desktop and mobile widths.

## UX Specification

### Primary User Flows
1. **Navigating to Task Detail:**
   - User clicks a task item from personal client overview (`/workspace/`), project details, or company workspace task board/list (`/workspaces/<ws_id>/tasks/`).
   - Browser lands on task detail view (`/tasks/<id>/` or `/workspaces/<ws_id>/tasks/<task_id>/`).
2. **Reviewing Task Content & Actions:**
   - Back link (`← Back to workspace` or `← Back to <Workspace> tasks`) sits top-left.
   - Eyebrow (`Task detail` or `<Workspace> / Tasks`) and primary heading (`<h1>`) span the full header region.
   - Task rich-text description block (`.task-description`) spans the available desktop container width.
   - Detail grid items (Assigned client, Status, Priority, Project, Due date, Last updated) display in a responsive grid.
   - Action controls (`Edit task`, `Delete task`) sit at the bottom in `.detail-actions`.

### Layout & Component States
- **Full-Width Shell Container:**
  - Remove fixed `max-width: 760px` restriction on `.detail-panel` for task detail pages (e.g. using `.detail-panel.task-page` or `max-width: none;`), aligning with `.detail-panel.project-page`.
- **Rich-Text Description Container (`.task-description`):**
  - Spans full inner content width with `24px` padding, `1px solid var(--line)` border, and `var(--white)` background.
  - Empty state renders `.form-note` (`No description added yet.`).
- **Metadata Grid (`.detail-grid`):**
  - Desktop (≥1024px): 2-column or auto-fit grid displaying key-value detail cards cleanly across full width.
  - Mobile (<700px): Collapses to single-column grid (`grid-template-columns: 1fr`).
- **Action Buttons (`.detail-actions`):**
  - Flexbox row with `12px` gap. Buttons expand to full width on mobile touch viewports.

### Responsive & Accessibility Requirements
- **Desktop (≥1024px):** Content matches full `.page-shell` width with topbar alignment, avoiding narrow column constraints.
- **Mobile (<768px):** Padding reduces to `52px 0`, metadata grid collapses to single column, action buttons stack vertically with touch targets ≥44px. Zero horizontal scroll overflow.
- **Keyboard & Screen Reader:**
  - Logical tab order starting from back link through description, metadata, and action buttons.
  - Visible focus indicators (`:focus-visible`) on back-link and action buttons.
  - Preserved `aria-label="Task description"` section landmark.

## Out of scope

- Redesigning task edit/create form layouts (`task_form.html`, `workspace_task_form.html`).
- Changing backend models, database migrations, views logic, or authorization rules.
- Adding new task fields, comments, attachment capabilities, or real-time status updates.
- Modifying authentication or non-task workspace pages.

## Implementation notes

- Inspect `.detail-panel` and `.page-shell` style rules in `core/static/core/landing.css`.
- Check whether `.detail-panel` should support a full-width variant or be aligned with the project page detail layout patterns introduced in `task-013`.
- Update `core/templates/core/task_detail.html` and `core/templates/core/workspace_task_detail.html` as needed.
- Have `@ux-developer` specify layout breakpoints, metadata grid wrapping rules, and responsive browser validation before code review.
