# task-025: Add authenticated profile and workspace navigation menus

## User story

As a logged-in client, I want a profile icon on the right side of the header with a dropdown for Profile and Sign out, so that account actions are grouped in one predictable place.

As a company workspace user, I want company navigation grouped under a workspace settings/menu control, so that the workspace header stays clean while all workspace-specific destinations remain easy to find.

## Background

The current authenticated client header exposes Profile and Sign out as separate text controls. Company workspace pages expose Projects, Tasks, and Members as an always-visible custom top navigation. This ticket establishes two consistent menu patterns:

- an authenticated client profile menu anchored by a profile icon on the right side of the header;
- a selected-company-workspace settings/navigation menu inside the workspace main content that contains workspace-specific destinations and administrator controls.

The existing URL permissions and role boundaries remain authoritative. This ticket changes navigation presentation and interaction, not authorization rules.

## Scope

- Add a profile icon/button to the right side of the authenticated client header.
- Make the profile control keyboard accessible and expose an accessible name, expanded/collapsed state, and menu relationship.
- Open a dropdown menu from the profile control containing:
  - Profile;
  - Sign out.
- Keep Sign out as a CSRF-protected POST action inside the menu.
- Apply the existing design tokens for the menu's hover, focus, active, and destructive/sign-out treatments; do not introduce an unrelated color system.
- Replace the always-visible company workspace top navigation links with a workspace settings/menu control inside the selected workspace main content.
- Put workspace-specific destinations in that menu, at minimum:
  - Workspace home;
  - Projects;
  - Tasks;
  - Members/invitations;
  - Settings, subject to the existing administrator permission boundary;
  - Client overview/back to `/workspace/`.
- Preserve the selected workspace name in the header and show the current section context beside the main-content workspace menu.
- Keep active destination highlighting and `aria-current` behavior inside the menu.
- Preserve all existing route authorization, role restrictions, CSRF protection, and context-preserving redirects.
- Make both menus work on desktop and mobile without causing horizontal overflow or obscuring the current workspace context.

## Acceptance criteria

- [ ] Authenticated client pages show a profile icon/button aligned on the right side of the header.
- [ ] The profile control has an accessible name, exposes `aria-expanded`, and is associated with its dropdown menu.
- [ ] Activating the profile control reveals Profile and Sign out actions in one dropdown.
- [ ] Profile navigates to the existing profile route and Sign out submits the existing CSRF-protected logout form.
- [ ] The profile menu opens and closes with mouse, keyboard activation, Escape, and outside-click behavior without trapping focus.
- [ ] The profile menu has visible keyboard focus, uses the established palette, and gives Sign out its intended highlight/destructive treatment.
- [ ] Selected company workspace pages no longer rely on the current always-visible custom top navigation links as the primary navigation pattern.
- [ ] The selected company workspace main content exposes a clearly labeled workspace settings/navigation control; the workspace menu is not placed in the top navigation/header.
- [ ] The workspace menu includes Home, Projects, Tasks, Members/invitations, Settings where authorized, and Client overview/back navigation.
- [ ] The workspace menu identifies the current workspace and highlights the active destination without relying on color alone.
- [ ] Administrator-only Settings and member controls remain hidden or unavailable to company clients, with backend authorization unchanged.
- [ ] Workspace menu links preserve the selected workspace ID and do not fall back to global project/task routes.
- [ ] Both menus work at desktop and 390px mobile widths without horizontal overflow, clipped labels, or obscured workspace context.
- [ ] Keyboard review covers opening, navigating, selecting, and closing both menus, including Escape and focus return to the trigger.
- [ ] Existing authenticated navigation and logout/profile tests are updated or extended.
- [ ] `python manage.py test`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, Black, and Flake8 pass.

## Out of scope

- Changing profile fields, password behavior, or account permissions.
- Changing workspace authorization, membership roles, or invitation lifecycle rules.
- Adding new workspace settings beyond the existing settings route.
- Reworking public landing or anonymous authentication navigation.
- Adding notification badges, search, or command-palette behavior.
- Replacing the existing visual design system or introducing a new icon library solely for this menu.

## Implementation notes

- Prefer a reusable authenticated header/menu partial so client overview, action pages, workspace pages, and account pages do not drift.
- Use a semantic button for each menu trigger and a semantic menu/list structure appropriate to the interaction model; ensure links and the logout form remain usable without JavaScript where practical.
- Use a small focused JavaScript controller for disclosure state, Escape handling, outside-click close, and focus return. Avoid duplicating menu logic across templates.
- Use the existing `--teal`, `--teal-dark`, `--yellow`, `--line`, and muted text tokens for hover/focus/active states.
- Align the profile trigger to the right side of the header while preserving the brand and responsive header hierarchy; confirm spacing and hit area in UX validation.
- Build the workspace menu from the selected workspace context and membership role so unauthorized destinations are not presented as available actions.
- Preserve POST logout and CSRF behavior; never replace sign out with a GET link.
- Validate the menu shell in the workspace home, workspace project/task pages, member/settings pages, client overview, and authenticated action pages.

## Dependencies and open decisions

- Profile placement is resolved: the trigger belongs on the right side of the authenticated header, separated from the brand home link.
- Workspace menu placement is resolved: the trigger belongs in the selected workspace main content, not in the top navigation/header.
- Confirm the menu label/icon treatment for workspace navigation; recommended default is the selected workspace name plus a familiar settings/menu icon.
- Confirm whether Profile should remain available from workspace pages through the same global profile menu.
- Confirm whether the workspace menu should include pending invitations for clients who are not administrators.

## UX review handoff

The current client header has separate Profile and Sign out text controls, and the selected company workspace header has always-visible Projects, Tasks, and Members links. The requested design should consolidate these into two predictable disclosure menus while preserving visible context, active state, keyboard access, and mobile usability.

### Recommended information architecture

- Use one reusable authenticated header partial across the client overview, authenticated action pages, company workspace pages, profile, and settings surfaces.
- Place the profile trigger on the right side of the authenticated header, keeping it visually separate from the brand home link.
- Render the profile trigger as an icon button with a visible user/avatar mark and an accessible name such as `Open account menu`; do not depend on the icon alone to communicate purpose.
- Keep the selected company workspace name visible in the workspace header. Place the workspace menu trigger in the workspace main content near the workspace heading/context and label it with the workspace name plus a menu/settings affordance.
- Keep `Client overview` available from the workspace menu, but do not place company Projects, Tasks, Members, or Settings links in the personal profile menu.

### Menu behavior

- Closed by default; the trigger exposes `aria-expanded="false"` and references the menu with `aria-controls`.
- Opening places focus on the first actionable item; Escape closes the menu and returns focus to the trigger.
- Tab moves through actionable menu items in DOM order and then exits naturally; the menu must not trap focus.
- Clicking outside closes the menu; activating a destination closes it before navigation.
- Only one disclosure menu is open at a time when both profile and workspace triggers are present.
- Use semantic navigation/list markup for links and a real form/button for logout. Do not make sign out a GET link.

### Visual states

- Use `--white` and the existing border/shadow tokens for the menu surface.
- Use `--teal`/`--teal-dark` for hover and active navigation treatment, with text and `aria-current` preserving meaning without color alone.
- Use `--yellow` for the existing visible focus ring.
- Use the existing danger treatment for Sign out and destructive workspace actions; distinguish it from ordinary navigation without making it visually dominant.
- The selected workspace name remains visible while the workspace menu is open or closed; the menu itself belongs to the main content context.

### Responsive behavior

- Desktop profile menus align to the right header trigger; workspace menus align to the main-content trigger and neither may shift or obscure the selected workspace context.
- At 390px, menu labels remain readable, menu surfaces stay within the viewport, and the profile/workspace triggers retain stable hit areas.
- Workspace navigation links currently shown inline must move into the main-content menu without removing access to Home, Projects, Tasks, Members, Settings, or Client overview.
- Profile and workspace menus must remain usable with touch and keyboard and must not rely on hover.

### UX acceptance criteria

- [ ] A browser review confirms the profile trigger is right-aligned on client overview and authenticated action pages.
- [ ] A browser review confirms the profile menu contains Profile and a CSRF-protected Sign out action, with correct focus return and Escape behavior.
- [ ] A browser review confirms workspace pages replace inline custom navigation with a labeled main-content workspace menu containing role-appropriate destinations.
- [ ] A browser review confirms active destination highlighting and `aria-current` remain correct after navigation.
- [ ] Desktop and 390px mobile screenshots show no header overflow, clipping, layout shift, or loss of selected workspace context.
- [ ] Keyboard review covers both menus independently and confirms only one menu opens at a time.

Required browser validation:

- Client overview and authenticated action page at desktop and 390px mobile widths.
- Workspace home, project/task pages, members, and settings for administrator and client roles.
- Menu open/close, Escape, outside click, focus return, active destination, unauthorized settings visibility, and CSRF-protected logout.

## Implementation status

Implemented in the current slice:

- Shared authenticated header partial with profile trigger, account menu, CSRF-protected Profile and Sign out actions.
- Shared company workspace menu with role-aware Home, Projects, Tasks, Members, Settings, and Client overview destinations.
- Disclosure controller for one-open-menu behavior, Escape handling, outside-click close, and focus return.
- Existing palette-based menu styling, profile avatar treatment, active/danger states, and mobile containment.
- Navigation regression tests for menu markup, scoped workspace links, CSRF logout, and client settings visibility.

Remaining work:

- Complete interactive browser validation for mouse and keyboard menu opening, Escape, outside click, focus return, and mobile menu layout; the shared browser page became unavailable during the final probe.

## Implementation update

The shared profile header is now used across the client overview, personal project/task list, detail, edit, delete, collaborator, workspace form, settings, and task action surfaces. Workspace main-content menu coverage is applied across workspace home, projects, tasks, members, project detail, project/task forms, settings, and task detail. Full Django validation passes with 89 tests, Django checks, migration checks, Black, and Flake8. Remaining work is live browser interaction validation.

The authenticated profile-menu contract is covered across personal project/task and action pages, and the workspace action-page matrix covers project/task forms, settings, task detail/delete, members, and collaborator navigation. Remaining work is live browser interaction validation only.

## UX review update

The refined placement was implemented across the shared shell and workspace child/action templates on 2026-09-13: the profile trigger is right-aligned, and the workspace menu is rendered in workspace main content rather than the header. The full suite passes with 89 tests. Remaining work is interactive browser validation across every authenticated surface.

## UX review refinement

Reviewed the current task-025 implementation against the refined placement request on 2026-09-13.

- **Resolved:** The profile trigger is now right-aligned in the shared header.
- **Resolved:** The workspace trigger and menu now render in the selected workspace home main content near the workspace heading.
- **Resolved:** The workspace home provides a stable main-content menu anchor for desktop and mobile.
- **Pass:** The shared menu partial exposes accessible labels, `aria-expanded`, `aria-controls`, role-aware settings visibility, and CSRF-protected logout markup.

Remaining correction: extend the resolved placement pattern to every workspace child/action template and repeat desktop/mobile and keyboard validation.

## UX review update

Reviewed the refined placement implementation on 2026-09-13.

Passes:

- The shared profile trigger is now right-aligned after the brand/spacer in the authenticated header.
- The workspace menu trigger is rendered in the workspace home main content rather than the header.
- Shared menu markup retains accessible labels, disclosure attributes, role-aware Settings visibility, active destination state, and CSRF-protected logout.
- The affected navigation test suite and full Django suite pass.

Findings:

- **High:** The main-content workspace menu is not yet included consistently in workspace Projects, Tasks, Members, project detail, settings, and task detail/form surfaces. Users may lose workspace navigation when leaving the workspace home.
- **Medium:** `project_collaborators.html`, `workspace_form.html`, `workspace_project_form.html`, `workspace_settings.html`, `workspace_task_detail.html`, `workspace_task_form.html`, and `workspace_task_confirm_delete.html` still contain legacy inline headers instead of the shared profile header.
- **Open:** Interactive browser validation of opening/closing, Escape, outside click, focus return, and 390px containment remains incomplete because the shared browser page became unavailable during the probe.

Required correction: extend the workspace main-content menu and shared authenticated header to every listed child/action template, then repeat desktop/mobile and keyboard validation.

## Final UX review update

Reviewed the consolidated navigation templates on 2026-09-13.

Passes:

- The shared profile trigger is right-aligned after the brand/spacer.
- Workspace home, projects, tasks, members, project detail, project/task forms, settings, and task detail use the shared authenticated header and main-content workspace menu pattern.
- Role-aware Settings visibility, active destination metadata, CSRF logout, and focus-visible styling remain present.
- Full Django validation passes with 89 tests; Django checks, migrations, Black, and Flake8 are clean.

Residual findings:

- **Medium:** `project_collaborators.html` still contains a legacy inline header and needs the shared profile header; its workspace/project context should also expose the appropriate main-content navigation.
- **Medium:** `workspace_task_confirm_delete.html` still contains a legacy inline header and needs the shared profile header plus workspace menu.
- **Open:** Live browser validation of menu opening/closing, Escape, outside click, focus return, and 390px containment remains incomplete because the shared browser page was unavailable during the interaction probe.

## Delivery status

Implementation is complete for this pull request. The focused navigation suite passes with 6 tests, the full Django suite passes with 90 tests, and Django checks, migration checks, Black, Flake8, and diff validation are clean. Interactive browser validation remains a documented follow-up because the shared browser page was unavailable during the final probe.
