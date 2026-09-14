from django.contrib.auth.models import User
from django.db import models
from django.db import transaction

from core.models import Project, WorkspaceMembership


def get_eligible_task_assignees(project: Project) -> models.QuerySet[User]:
    """Return a queryset of users eligible to be assigned to tasks in the project."""
    user_ids = {project.client_id}

    project_member_ids = project.memberships.filter(is_active=True).values_list(
        "user_id", flat=True
    )
    user_ids.update(project_member_ids)

    if project.workspace_id:
        workspace_member_ids = project.workspace.memberships.filter(
            is_active=True
        ).values_list("user_id", flat=True)
        user_ids.update(workspace_member_ids)

    return User.objects.filter(id__in=user_ids).order_by("username")


class LastAdministratorError(Exception):
    """Raised when a change would leave a company workspace without an admin."""


def change_membership_role(
    membership: WorkspaceMembership, role: str
) -> WorkspaceMembership:
    """Change a membership role while preserving the last-admin invariant."""
    with transaction.atomic():
        locked_membership = WorkspaceMembership.objects.select_for_update().get(
            pk=membership.pk
        )
        if (
            locked_membership.role == WorkspaceMembership.Role.ADMIN
            and role != WorkspaceMembership.Role.ADMIN
            and not _has_another_active_admin(locked_membership)
        ):
            raise LastAdministratorError
        locked_membership.role = role
        locked_membership.save(update_fields=["role"])
        return locked_membership


def deactivate_membership(membership: WorkspaceMembership) -> WorkspaceMembership:
    """Deactivate a membership while preserving the last-admin invariant."""
    with transaction.atomic():
        locked_membership = WorkspaceMembership.objects.select_for_update().get(
            pk=membership.pk
        )
        if (
            locked_membership.role == WorkspaceMembership.Role.ADMIN
            and not _has_another_active_admin(locked_membership)
        ):
            raise LastAdministratorError
        locked_membership.is_active = False
        locked_membership.save(update_fields=["is_active"])
        return locked_membership


def _has_another_active_admin(membership: WorkspaceMembership) -> bool:
    """Return whether another active administrator exists in the same workspace."""
    return (
        WorkspaceMembership.objects.select_for_update()
        .filter(
            workspace=membership.workspace,
            role=WorkspaceMembership.Role.ADMIN,
            is_active=True,
        )
        .exclude(pk=membership.pk)
        .exists()
    )
