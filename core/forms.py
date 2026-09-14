from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from typing import Optional

from core.models import (
    Project,
    ProjectInvitation,
    ProjectMembership,
    Task,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from core.sanitization import clean_rich_text
from core.services import get_eligible_task_assignees


class ClientRegistrationForm(UserCreationForm):
    """Create a regular user and grant membership in the Client group."""

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit: bool = True) -> User:
        """Save the user and assign the standard client authorization group."""
        user = super().save(commit=commit)
        if commit:
            client_group, _ = Group.objects.get_or_create(name="Client")
            user.groups.add(client_group)
            workspace = Workspace.objects.create(
                name=f"{user.username}'s workspace", kind=Workspace.Kind.PERSONAL
            )
            WorkspaceMembership.objects.create(
                workspace=workspace,
                user=user,
                role=WorkspaceMembership.Role.ADMIN,
            )
        return user


class WorkspaceCreateForm(forms.ModelForm):
    """Validate creation of a company workspace."""

    class Meta:
        model = Workspace
        fields = ("name",)

    def clean_name(self) -> str:
        """Reject empty or duplicate workspace names for the creator."""
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter a workspace name.")
        return name


class WorkspaceSettingsForm(forms.ModelForm):
    """Validate editable company workspace settings."""

    class Meta:
        model = Workspace
        fields = ("name",)

    def clean_name(self) -> str:
        """Require a non-empty workspace name."""
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter a workspace name.")
        return name


class WorkspaceInviteForm(forms.Form):
    """Invite an existing Client user to a company workspace."""

    username = forms.CharField(
        max_length=150,
        label="Client username",
        help_text="Enter the username of an existing Client user.",
    )

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        inviter: User,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.inviter = inviter

    def clean_username(self) -> str:
        """Validate that the target is an eligible workspace client."""
        username = self.cleaned_data["username"]
        try:
            invitee = User.objects.get(username=username)
        except User.DoesNotExist as error:
            raise forms.ValidationError("Enter an existing Client username.") from error
        if invitee == self.inviter:
            raise forms.ValidationError("You cannot invite yourself.")
        if not invitee.groups.filter(name="Client").exists():
            raise forms.ValidationError("The user must be a Client user.")
        if WorkspaceMembership.objects.filter(
            workspace=self.workspace, user=invitee, is_active=True
        ).exists():
            raise forms.ValidationError("This client is already a workspace member.")
        if WorkspaceInvitation.objects.filter(
            workspace=self.workspace,
            invitee=invitee,
            status=WorkspaceInvitation.Status.PENDING,
        ).exists():
            raise forms.ValidationError("This client is already invited.")
        self.invitee = invitee
        return username


class TaskForm(forms.ModelForm):
    """Validate client-editable task fields."""

    class Meta:
        model = Task
        fields = (
            "project",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "assigned_to",
        )
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(
        self,
        *args: object,
        client: User,
        projects=None,
        project_context: Optional[Project] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = (
            projects if projects is not None else Project.objects.filter(client=client)
        )
        if project_context is not None:
            self.fields["project"].queryset = Project.objects.filter(
                pk=project_context.pk
            )
            self.fields["project"].initial = project_context.pk
            self.fields["project"].disabled = True

        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].label = "Assigned client"
        self.fields["assigned_to"].help_text = (
            "Select a client who belongs to this project or workspace."
        )
        self.fields["assigned_to"].empty_label = "Unassigned"

        target_project = project_context
        if (
            target_project is None
            and self.instance
            and getattr(self.instance, "project_id", None)
        ):
            target_project = self.instance.project
        if target_project is None and self.is_bound:
            p_id = self.data.get("project")
            if p_id:
                try:
                    target_project = self.fields["project"].queryset.get(pk=p_id)
                except (Project.DoesNotExist, ValueError, TypeError):
                    target_project = None

        if target_project is not None:
            self.fields["assigned_to"].queryset = get_eligible_task_assignees(
                target_project
            )
        else:
            allowed_projects = self.fields["project"].queryset
            user_ids = set()
            for p in allowed_projects.select_related("workspace"):
                user_ids.add(p.client_id)
                user_ids.update(
                    p.memberships.filter(is_active=True).values_list(
                        "user_id", flat=True
                    )
                )
                if p.workspace_id:
                    user_ids.update(
                        p.workspace.memberships.filter(is_active=True).values_list(
                            "user_id", flat=True
                        )
                    )
            self.fields["assigned_to"].queryset = User.objects.filter(
                id__in=user_ids
            ).order_by("username")

    def clean_description(self) -> str:
        """Sanitize rich-text content before saving it."""
        return clean_rich_text(self.cleaned_data.get("description", ""))


class ProjectForm(forms.ModelForm):
    """Validate project names and workspace access for the authenticated client."""

    class Meta:
        model = Project
        fields = ("workspace", "name", "description")

    def __init__(
        self,
        *args: object,
        client: User,
        workspaces=None,
        workspace_context: Optional[Workspace] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.client_user = client
        self.fields["workspace"].required = False
        if workspaces is not None:
            self.fields["workspace"].queryset = workspaces
        if workspace_context is not None:
            self.fields["workspace"].queryset = Workspace.objects.filter(
                pk=workspace_context.pk
            )
            self.fields["workspace"].initial = workspace_context.pk
            self.fields["workspace"].disabled = True
        if self.is_bound:
            for field_name, field in self.fields.items():
                if self.errors.get(field_name):
                    field.widget.attrs["aria-invalid"] = "true"
                    field_id = self[field_name].auto_id
                    field.widget.attrs["aria-describedby"] = f"{field_id}-error"

    def clean_name(self) -> str:
        """Reject duplicate project names for the current client."""
        name = self.cleaned_data["name"]
        duplicate_projects = Project.objects.filter(client=self.client_user, name=name)
        if self.instance.pk:
            duplicate_projects = duplicate_projects.exclude(pk=self.instance.pk)
        if duplicate_projects.exists():
            raise forms.ValidationError("You already have a project with this name.")
        return name


class ProjectInviteForm(forms.Form):
    """Invite an existing Client user to a project."""

    username = forms.CharField(
        max_length=150,
        label="Client username",
        help_text="Enter the username of an existing Client user.",
    )

    def __init__(
        self, *args: object, project: Project, inviter: User, **kwargs: object
    ):
        super().__init__(*args, **kwargs)
        self.project = project
        self.inviter = inviter
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "off",
                "role": "combobox",
                "aria-autocomplete": "list",
                "aria-controls": "invite-suggestions",
                "aria-expanded": "false",
            }
        )

    def clean_username(self) -> str:
        """Validate that the target is an eligible, non-member Client user."""
        username = self.cleaned_data["username"]
        try:
            invitee = User.objects.get(username=username)
        except User.DoesNotExist as error:
            raise forms.ValidationError("Enter an existing Client username.") from error
        if invitee == self.inviter:
            raise forms.ValidationError("You cannot invite yourself.")
        if not invitee.groups.filter(name="Client").exists():
            raise forms.ValidationError("The user must be a Client user.")
        if ProjectMembership.objects.filter(
            project=self.project, user=invitee, is_active=True
        ).exists():
            raise forms.ValidationError(
                "This client already collaborates on the project."
            )
        if ProjectInvitation.objects.filter(
            project=self.project,
            invitee=invitee,
            status=ProjectInvitation.Status.PENDING,
        ).exists():
            raise forms.ValidationError("This client is already invited.")
        self.invitee = invitee
        return username


class ClientProfileForm(forms.ModelForm):
    """Validate personal fields a client may update on their profile."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
