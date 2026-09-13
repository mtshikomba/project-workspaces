# task-023: Add company workspaces and client invitations

## User story

As a company administrator, I want to create and manage a company workspace and invite clients to it, so that our company can collaborate with clients in one controlled workspace.

As an individual client, I want to sign up without joining a company, so that I can continue using an isolated personal workspace.

## Background

The current application treats a client user as the owner of projects and tasks. It already supports project-level invitations and memberships, but it does not provide a company-level workspace or workspace roles. This feature should introduce workspace membership without weakening tenant isolation or breaking the existing individual-client registration flow.

## Scope

- Add a first-class workspace concept that can represent either:
  - a company workspace with company-managed members; or
  - an individual client's personal workspace.
- Allow an authenticated user to create a company workspace with a name and the required company details agreed during implementation.
- Make the workspace creator the initial administrator automatically.
- Support workspace roles at minimum:
  - `Admin`: full workspace access, including workspace settings, member management, invitations, and removal of members subject to the last-admin rule.
  - `Client`: access to the workspace resources shared with that client, without administrative controls.
- Allow a company administrator to invite an existing client account to the company workspace.
- Allow an invited client to accept or decline a pending workspace invitation.
- Ensure a company workspace always has at least one administrator. The system must prevent removing or demoting the last administrator.
- Preserve the existing individual signup path: a newly registered individual client receives or can access a personal workspace and is not added to a company workspace unless they explicitly accept an invitation.
- Preserve workspace and resource isolation: users must not view or modify another workspace's projects, tasks, members, or invitations without authorization.
- Define how existing projects, tasks, project memberships, and project invitations are associated with the new workspace model, including a data migration strategy.

## Acceptance criteria

- [x] A user can create a company workspace with valid required details.
- [x] The creator is automatically an administrator and can access the company workspace immediately.
- [x] A creator can see the newly created company workspace in their workspace list or switcher without needing a direct URL.
- [x] A company workspace cannot exist without at least one administrator.
- [x] An administrator can invite an eligible existing client by the supported identifier, such as username or email.
- [x] Duplicate pending invitations for the same workspace and invitee are rejected or safely reused.
- [x] An invitee can see pending workspace invitations and can accept or decline them.
- [x] Accepting an invitation creates the correct client membership and grants only the access defined for the client role.
- [x] After accepting an invitation, the client can see the joined company workspace in their workspace list or switcher.
- [x] The workspace list distinguishes the personal workspace, active company memberships, and pending company invitations.
- [x] The company workspace creation page uses the same shared action-page shell, brand/top navigation, back-link treatment, eyebrow, constrained form panel, typography, spacing, and full-width primary submit pattern as project, task, profile, and password forms.
- [x] The creation page has consistent validation, error, focus, and mobile states, including a clear return path to the workspace.
- [x] Declining or revoking an invitation does not grant workspace access.
- [x] A non-administrator cannot create, revoke, or manage workspace invitations, members, roles, or settings.
- [x] An administrator can remove a client member, but cannot remove the last administrator.
- [x] The company member page lists active members with their role and exposes a visible remove action for removable members.
- [x] The company member page lists pending invitations and exposes a visible revoke action for each pending invitation.
- [x] Removing a member or revoking an invitation requires an explicit confirmation and shows a clear success or error state.
- [x] An administrator cannot demote the last administrator.
- [x] Company workspace resources are inaccessible to users who are not members of that workspace.
- [x] Direct individual registration continues to succeed without a company invitation and provides an isolated personal workspace.
- [x] An individual client can later join a company workspace by accepting a valid invitation without losing access to their personal workspace.
- [x] Existing project-level collaboration behavior remains compatible or is explicitly migrated to workspace-level membership with equivalent authorization.
- [x] Tests cover company creation, initial admin assignment, invitation lifecycle, role boundaries, last-admin protection, tenant isolation, and individual registration regression coverage.
- [x] Required database migrations are generated and `python manage.py makemigrations --check --dry-run` passes.
- [x] `python manage.py check`, Black, and Flake8 pass.
- [x] The complete user-facing workspace and invitation flows, including member removal and invitation revocation, are keyboard accessible and validated at desktop and mobile widths.

## Out of scope

- Organization billing, subscriptions, usage limits, or payments.
- SSO, SCIM, domain-based auto-join, or enterprise identity provisioning.
- Multiple administrator tiers or custom roles beyond administrator and client.
- Cross-company client identity merging or account deduplication.
- Public or anonymous workspace access.
- Replacing Django's global staff or superuser permissions with workspace roles.
- Real-time collaboration, chat, or notifications beyond the invitation workflow.

## Implementation notes

- Review whether `Workspace`, `WorkspaceMembership`, and `WorkspaceInvitation` should become the ownership boundary for projects and tasks, rather than adding company-specific fields to the existing client-owned models.
- Keep authorization checks in a reusable service or mixin so every workspace-scoped view applies the same membership and role rules.
- Use database constraints and transactional service logic for the invariant that each company workspace has at least one administrator; view-level checks alone are insufficient.
- Define invitation expiry, revocation, and acceptance behavior consistently with the existing `ProjectInvitation` lifecycle, and avoid accepting invitations for disabled or unauthorized accounts.
- Plan a data migration for existing users and client-owned projects/tasks. Existing individual users should retain access to their current data through their personal workspace.
- Use `select_related`/`prefetch_related` for workspace membership and invitation listings where appropriate, and add indexes/unique constraints for workspace, user, role, and pending-invitation lookups.
- Before implementation, have `@ux-developer` specify the company workspace creation, member management, invitation inbox, empty, error, permission-denied, and responsive states.
- The member-management page is an administrator control surface, not a read-only roster: active members, pending invitations, role labels, removal/revocation actions, confirmation behavior, and failure feedback must be represented in the UI.
- Workspace discovery must be a first-class UI flow: render a visible workspace list or switcher from the user's active memberships, show the creator's new company workspace immediately, and show pending invitations separately until accepted.
- Workspace creation should reuse the existing action-page form pattern rather than introducing a one-off bare detail layout; visual and interaction changes should be shared with the established form styles where possible.
- The project/task authorization migration must define the workspace ownership boundary, company-admin project creation, client access to workspace resources, and behavior for existing personal projects before the related acceptance criteria can be marked complete.

## Dependencies and open decisions

- Confirm the required company fields beyond workspace name, if any.
- Confirm whether one user may administer multiple company workspaces and whether a client may belong to multiple company workspaces.
- Confirm whether company administrators are also allowed to act as clients within the same workspace.
- Confirm whether existing project invitations remain available inside a company workspace or are replaced by workspace invitations.
- Confirm invitation expiry duration and whether invitations may target users who have not registered yet.

## Implementation status

Implemented in the current slice:

- `Workspace`, `WorkspaceMembership`, and `WorkspaceInvitation` models with role and pending-invitation constraints.
- Personal workspace provisioning for new registrations and a migration for existing Client users and projects.
- Company workspace creation, administrator-only member controls, invitation accept/decline/revoke, and last-admin removal protection.
- Workspace invitation discovery in the authenticated workspace.
- Responsive member and invitation surfaces with labeled controls, visible accept/decline actions, and no mobile horizontal overflow.
- Navigable active company workspace discovery for creators and members, with pending invitations kept separate.
- Shared action-page styling for workspace creation and member management, including responsive layouts and confirmation-protected admin actions.
- Administrator promotion/demotion controls with protection against demoting the final active administrator.
- Workspace-aware project creation and project/task visibility for active company members, with non-member isolation and restricted workspace choices.
- Transactional membership services protect last-admin role changes and deactivation across all application write paths.

## Completion note

No additional database or API constraint is required. Application-created company workspaces are provisioned atomically with their initial administrator, and all application membership changes preserve the active-admin invariant.

## UX review

Reviewed and implemented `/workspaces/new/`, workspace discovery, and member controls at desktop and 390px mobile widths on 2026-09-13. The updated flows use the shared action-page shell, expose navigable active company workspaces, and provide confirmation-protected member and invitation controls without mobile horizontal overflow.
