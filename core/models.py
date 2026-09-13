import uuid

from django.contrib.auth.models import User
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from core.sanitization import clean_rich_text


class Workspace(models.Model):
    """A personal or company-owned collaboration boundary."""

    class Kind(models.TextChoices):
        PERSONAL = "personal", "Personal"
        COMPANY = "company", "Company"

    name = models.CharField(
        max_length=200,
        verbose_name="name",
        help_text="The display name of this workspace.",
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.PERSONAL,
        verbose_name="kind",
        help_text="Whether this workspace is personal or company-owned.",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When this workspace was created.",
    )

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "workspace"
        verbose_name_plural = "workspaces"

    def __str__(self) -> str:
        return self.name


class WorkspaceMembership(models.Model):
    """Grant a user an active role within a workspace."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CLIENT = "client", "Client"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="workspace",
        help_text="The workspace this membership belongs to.",
        db_index=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
        verbose_name="user",
        help_text="The user granted workspace access.",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name="role",
        help_text="The user's role within this workspace.",
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="active",
        help_text="Whether this membership currently grants access.",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When this membership was created.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "user"), name="unique_workspace_membership"
            )
        ]
        verbose_name = "workspace membership"
        verbose_name_plural = "workspace memberships"


class WorkspaceInvitation(models.Model):
    """Represent a single-use invitation to join a company workspace."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        REVOKED = "revoked", "Revoked"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invitations",
        verbose_name="workspace",
        help_text="The company workspace this invitation grants access to.",
        db_index=True,
    )
    inviter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_workspace_invitations",
        verbose_name="inviter",
        help_text="The administrator who sent this invitation.",
    )
    invitee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_workspace_invitations",
        verbose_name="invitee",
        help_text="The client who may accept this invitation.",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="invitation token",
        help_text="The opaque invitation identifier.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="status",
        help_text="The current invitation lifecycle state.",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When this invitation was created.",
    )
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="accepted at",
        help_text="When the invitee accepted this invitation.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "invitee"),
                condition=models.Q(status="pending"),
                name="unique_pending_workspace_invitation",
            )
        ]
        verbose_name = "workspace invitation"
        verbose_name_plural = "workspace invitations"

    @property
    def is_pending(self) -> bool:
        """Return whether the invitation can still be accepted."""
        return self.status == self.Status.PENDING


class Project(models.Model):
    """A project owned by a client and containing the client's tasks."""

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="client_projects",
        verbose_name="client",
        help_text="The client user who owns this project.",
        db_index=True,
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name="workspace",
        help_text="The workspace containing this project.",
        db_index=True,
    )
    name = models.CharField(
        max_length=200,
        verbose_name="name",
        help_text="A name that identifies the project.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="description",
        help_text="Optional context about the project.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When the project was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="updated at",
        help_text="When the project was last changed.",
    )

    class Meta:
        ordering = ("-updated_at", "name")
        verbose_name = "project"
        verbose_name_plural = "projects"
        constraints = [
            models.UniqueConstraint(
                fields=("client", "name"), name="unique_project_name_per_client"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """Return the client-facing detail URL for this project."""
        from django.urls import reverse

        return reverse("project-detail", kwargs={"pk": self.pk})


class ProjectMembership(models.Model):
    """Grant an accepted client access to a project and its tasks."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="project",
        help_text="The project shared with this client.",
        db_index=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        verbose_name="client",
        help_text="The client who accepted access to this project.",
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="active",
        help_text="Whether this client currently has project access.",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When project access was granted.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "user"), name="unique_project_membership"
            )
        ]
        verbose_name = "project membership"
        verbose_name_plural = "project memberships"


class ProjectInvitation(models.Model):
    """Represent a single-use invitation to join a client project."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        REVOKED = "revoked", "Revoked"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="invitations",
        verbose_name="project",
        help_text="The project this invitation grants access to.",
        db_index=True,
    )
    inviter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_project_invitations",
        verbose_name="inviter",
        help_text="The project owner who sent this invitation.",
    )
    invitee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_project_invitations",
        verbose_name="invitee",
        help_text="The client who may accept this invitation.",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="invitation token",
        help_text="The opaque single-use invitation identifier.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="status",
        help_text="The current invitation lifecycle state.",
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="created at",
        help_text="When this invitation was created.",
    )
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="accepted at",
        help_text="When the invitee accepted this invitation.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "invitee"),
                condition=models.Q(status="pending"),
                name="unique_pending_project_invitation",
            )
        ]
        verbose_name = "project invitation"
        verbose_name_plural = "project invitations"

    @property
    def is_pending(self) -> bool:
        """Return whether the invitation can still be accepted."""
        return self.status == self.Status.PENDING


class Task(models.Model):
    """A task owned by a client user."""

    class Status(models.TextChoices):
        OUTSTANDING = "outstanding", "Outstanding"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="client_tasks",
        verbose_name="client",
        help_text="The client user who owns this task.",
        db_index=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="project",
        help_text="The project containing this task.",
        db_index=True,
    )
    title = models.CharField(
        max_length=200,
        verbose_name="title",
        help_text="A short description of the task.",
    )
    description = CKEditor5Field(
        blank=True,
        config_name="default",
        verbose_name="description",
        help_text="Rich-text context and notes for the task.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OUTSTANDING,
        verbose_name="status",
        help_text="The current workflow status of the task.",
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="priority",
        help_text="The relative urgency of the task.",
    )
    due_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="due date",
        help_text="The date by which the task should be completed.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="updated at",
        help_text="The last time the task was changed.",
    )

    class Meta:
        ordering = ("-updated_at", "title")
        verbose_name = "task"
        verbose_name_plural = "tasks"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        """Return the client-facing detail URL for this task."""
        from django.urls import reverse

        return reverse("task-detail", kwargs={"pk": self.pk})

    def get_safe_description(self) -> str:
        """Return the task description with unsafe markup removed."""
        return clean_rich_text(self.description)
