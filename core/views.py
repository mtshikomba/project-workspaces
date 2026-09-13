from django.http import Http404, HttpRequest, JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, F, Q, QuerySet
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    TemplateView,
    UpdateView,
)
from django.contrib.auth.views import PasswordChangeView
from typing import Iterable

from core.forms import (
    ClientProfileForm,
    ClientRegistrationForm,
    ProjectForm,
    ProjectInviteForm,
    TaskForm,
    WorkspaceCreateForm,
    WorkspaceInviteForm,
    WorkspaceSettingsForm,
)
from django.contrib.auth.models import User

from core.models import (
    Project,
    ProjectInvitation,
    ProjectMembership,
    Task,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from core.services import (
    LastAdministratorError,
    change_membership_role,
    deactivate_membership,
)


def build_task_lanes(tasks: Iterable[Task]) -> list[dict[str, object]]:
    """Group tasks into the stable status order used by task boards."""
    return [
        {
            "value": status.value,
            "label": status.label,
            "tasks": [task for task in tasks if task.status == status.value],
        }
        for status in Task.Status
    ]


class ClientAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to authenticated users in the Client group."""

    login_url = "/accounts/login/"

    def test_func(self) -> bool:
        """Return whether the current user has client access."""
        return self.request.user.groups.filter(name="Client").exists()


class ClientRegistrationView(CreateView):
    """Render and process the public client registration form."""

    form_class = ClientRegistrationForm
    template_name = "registration/register.html"
    success_url = "/accounts/login/"


class WorkspaceCreateView(ClientAccessMixin, CreateView):
    """Create a company workspace and make the creator its administrator."""

    model = Workspace
    form_class = WorkspaceCreateForm
    template_name = "core/workspace_form.html"
    success_url = reverse_lazy("client-landing")

    def form_valid(self, form: WorkspaceCreateForm):
        """Create the workspace and its initial admin atomically."""
        with transaction.atomic():
            form.instance.kind = Workspace.Kind.COMPANY
            response = super().form_valid(form)
            WorkspaceMembership.objects.create(
                workspace=self.object,
                user=self.request.user,
                role=WorkspaceMembership.Role.ADMIN,
            )
        return response


class WorkspaceAdminMixin(ClientAccessMixin):
    """Restrict workspace management to active workspace administrators."""

    def get_workspace(self, pk: int) -> Workspace:
        """Return a company workspace administered by the current user."""
        membership = (
            WorkspaceMembership.objects.filter(
                workspace_id=pk,
                user=self.request.user,
                role=WorkspaceMembership.Role.ADMIN,
                is_active=True,
                workspace__kind=Workspace.Kind.COMPANY,
            )
            .select_related("workspace")
            .first()
        )
        if membership is None:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return membership.workspace


class WorkspaceContextMixin(ClientAccessMixin):
    """Provide a selected company workspace to workspace-scoped views."""

    workspace: Workspace
    membership: WorkspaceMembership

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object):
        """Validate active membership before serving a workspace route."""
        self.membership = get_object_or_404(
            WorkspaceMembership.objects.select_related("workspace"),
            workspace_id=kwargs["pk"],
            user=request.user,
            is_active=True,
            workspace__kind=Workspace.Kind.COMPANY,
        )
        self.workspace = self.membership.workspace
        return super().dispatch(request, *args, **kwargs)

    def workspace_context(self) -> dict[str, object]:
        """Return shared shell context for the selected workspace."""
        return {
            "workspace": self.workspace,
            "membership": self.membership,
            "workspace_memberships": WorkspaceMembership.objects.filter(
                user=self.request.user,
                is_active=True,
                workspace__kind=Workspace.Kind.COMPANY,
            ).select_related("workspace"),
        }


class WorkspaceHomeView(WorkspaceContextMixin, TemplateView):
    """Display the selected company workspace home."""

    template_name = "core/workspace_home.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add selected workspace projects and tasks to the workspace shell."""
        context = super().get_context_data(**kwargs)
        projects = Project.objects.filter(workspace=self.workspace).annotate(
            task_count=Count("tasks")
        )
        context.update(self.workspace_context())
        context["projects"] = projects
        context["tasks"] = Task.objects.filter(project__workspace=self.workspace)
        return context


class WorkspaceProjectListView(WorkspaceContextMixin, TemplateView):
    """List projects inside the selected company workspace."""

    template_name = "core/workspace_projects.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add selected workspace projects to the shared shell."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        context["projects"] = Project.objects.filter(workspace=self.workspace).annotate(
            task_count=Count("tasks")
        )
        return context


class WorkspaceProjectDetailView(WorkspaceContextMixin, DetailView):
    """Display a company project and its shared task board."""

    model = Project
    template_name = "core/workspace_project_detail.html"

    def get_object(self, queryset=None) -> Project:
        """Return only the project in the selected workspace."""
        return get_object_or_404(
            Project, pk=self.kwargs["project_id"], workspace=self.workspace
        )

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add the selected project's shared task-board context."""
        context = super().get_context_data(**kwargs)
        tasks = list(self.object.tasks.select_related("project"))
        context.update(self.workspace_context())
        context["tasks"] = tasks
        context["task_lanes"] = build_task_lanes(tasks)
        context["task_statuses"] = Task.Status.choices
        context["task_view_label"] = "Project tasks"
        return context


class WorkspaceProjectCreateView(WorkspaceContextMixin, CreateView):
    """Create a project directly inside the selected company workspace."""

    model = Project
    form_class = ProjectForm
    template_name = "core/workspace_project_form.html"

    def get_form_kwargs(self) -> dict[str, object]:
        """Limit the form to the selected workspace."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["workspaces"] = Workspace.objects.filter(pk=self.workspace.pk)
        return kwargs

    def form_valid(self, form: ProjectForm):
        """Assign the selected workspace from the route, never form data."""
        form.instance.client = self.request.user
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add selected workspace navigation context to the form."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        return context

    def get_success_url(self) -> str:
        """Return to the selected workspace project list."""
        return reverse_lazy("workspace-projects", kwargs={"pk": self.workspace.pk})


class WorkspaceTaskListView(WorkspaceContextMixin, TemplateView):
    """List tasks inside the selected company workspace."""

    template_name = "core/workspace_tasks.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add selected workspace tasks to the shared shell."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        tasks = list(
            Task.objects.filter(project__workspace=self.workspace).select_related(
                "project"
            )
        )
        context["tasks"] = tasks
        context["task_lanes"] = build_task_lanes(tasks)
        context["task_statuses"] = Task.Status.choices
        context["task_view_label"] = "Workspace tasks"
        return context


class WorkspaceTaskCreateView(WorkspaceContextMixin, CreateView):
    """Create a task for a project inside the selected company workspace."""

    model = Task
    form_class = TaskForm
    template_name = "core/workspace_task_form.html"

    def get_form_kwargs(self) -> dict[str, object]:
        """Limit project choices to the selected workspace."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["projects"] = Project.objects.filter(workspace=self.workspace)
        return kwargs

    def form_valid(self, form: TaskForm):
        """Assign task ownership from the selected workspace project."""
        form.instance.client = form.cleaned_data["project"].client
        return super().form_valid(form)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add selected workspace navigation context to the form."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        return context

    def get_success_url(self) -> str:
        """Return to the selected workspace task list."""
        return reverse_lazy("workspace-tasks", kwargs={"pk": self.workspace.pk})


class WorkspaceTaskContextMixin(WorkspaceContextMixin):
    """Provide a selected workspace and task to task mutation views."""

    task: Task

    def get_task(self, task_id: int) -> Task:
        """Return a task belonging to the selected workspace."""
        return get_object_or_404(
            Task.objects.select_related("project"),
            pk=task_id,
            project__workspace=self.workspace,
        )


class WorkspaceTaskDetailView(WorkspaceTaskContextMixin, DetailView):
    """Display a task inside the selected company workspace."""

    model = Task
    template_name = "core/workspace_task_detail.html"

    def get_object(self, queryset=None) -> Task:
        """Return only the selected workspace task."""
        return self.get_task(self.kwargs["task_id"])

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add shared workspace navigation context."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        return context


class WorkspaceTaskUpdateView(WorkspaceTaskContextMixin, UpdateView):
    """Update a task while preserving the selected workspace context."""

    model = Task
    form_class = TaskForm
    template_name = "core/workspace_task_form.html"

    def get_object(self, queryset=None) -> Task:
        """Return only the selected workspace task."""
        return self.get_task(self.kwargs["task_id"])

    def get_form_kwargs(self) -> dict[str, object]:
        """Limit editable project choices to the selected workspace."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["projects"] = Project.objects.filter(workspace=self.workspace)
        return kwargs

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add shared workspace navigation context."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        return context

    def get_success_url(self) -> str:
        """Return to the selected workspace task detail page."""
        return reverse_lazy(
            "workspace-task-detail",
            kwargs={"pk": self.workspace.pk, "task_id": self.object.pk},
        )


class WorkspaceTaskStatusView(WorkspaceTaskContextMixin, View):
    """Update task status inside the selected workspace."""

    def post(self, request: HttpRequest, pk: int, task_id: int) -> JsonResponse:
        """Persist a valid status for the selected workspace task."""
        task = self.get_task(task_id)
        status = request.POST.get("status")
        valid_statuses = {choice.value: choice.label for choice in Task.Status}
        if status not in valid_statuses:
            return JsonResponse({"error": "Invalid task status."}, status=400)
        task.status = status
        task.save(update_fields=["status", "updated_at"])
        return JsonResponse({"status": status, "label": valid_statuses[status]})


class WorkspaceTaskDeleteView(WorkspaceTaskContextMixin, DeleteView):
    """Delete a task while preserving selected workspace context."""

    model = Task
    template_name = "core/workspace_task_confirm_delete.html"

    def get_object(self, queryset=None) -> Task:
        """Return only the selected workspace task."""
        return self.get_task(self.kwargs["task_id"])

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add shared workspace navigation context."""
        context = super().get_context_data(**kwargs)
        context.update(self.workspace_context())
        return context

    def get_success_url(self) -> str:
        """Return to the selected workspace task list."""
        return reverse_lazy("workspace-tasks", kwargs={"pk": self.workspace.pk})


class WorkspaceSettingsView(WorkspaceAdminMixin, UpdateView):
    """Allow company administrators to update selected workspace settings."""

    model = Workspace
    form_class = WorkspaceSettingsForm
    template_name = "core/workspace_settings.html"

    def get_object(self, queryset=None) -> Workspace:
        """Return the administered workspace from the route."""
        return self.get_workspace(self.kwargs["pk"])

    def get_success_url(self) -> str:
        """Return to the selected workspace after saving settings."""
        return reverse_lazy("workspace-home", kwargs={"pk": self.object.pk})


class WorkspaceMemberListView(WorkspaceAdminMixin, View):
    """Display company workspace members to an administrator."""

    def get(self, request: HttpRequest, pk: int):
        """Render the member management page."""
        workspace = self.get_workspace(pk)
        return render(
            request,
            "core/workspace_members.html",
            {
                "workspace": workspace,
                "form": WorkspaceInviteForm(workspace=workspace, inviter=request.user),
                "memberships": workspace.memberships.filter(
                    is_active=True
                ).select_related("user"),
                "invitations": workspace.invitations.filter(
                    status=WorkspaceInvitation.Status.PENDING
                ).select_related("invitee"),
            },
        )


class WorkspaceInviteView(WorkspaceAdminMixin, View):
    """Create pending invitations for a company workspace."""

    def post(self, request: HttpRequest, pk: int):
        """Invite an eligible client to the administered workspace."""
        workspace = self.get_workspace(pk)
        form = WorkspaceInviteForm(
            request.POST, workspace=workspace, inviter=request.user
        )
        if not form.is_valid():
            return render(
                request,
                "core/workspace_members.html",
                {
                    "workspace": workspace,
                    "form": form,
                    "memberships": workspace.memberships.filter(
                        is_active=True
                    ).select_related("user"),
                    "invitations": workspace.invitations.filter(
                        status=WorkspaceInvitation.Status.PENDING
                    ).select_related("invitee"),
                },
                status=200,
            )
        WorkspaceInvitation.objects.create(
            workspace=workspace,
            inviter=request.user,
            invitee=form.invitee,
        )
        return redirect("client-landing")


class WorkspaceMemberRemoveView(WorkspaceAdminMixin, View):
    """Deactivate a company workspace member without deleting their account."""

    def post(self, request: HttpRequest, pk: int, membership_id: int):
        """Remove a member while preserving the last-admin invariant."""
        workspace = self.get_workspace(pk)
        membership = get_object_or_404(
            WorkspaceMembership,
            pk=membership_id,
            workspace=workspace,
            is_active=True,
        )
        try:
            deactivate_membership(membership)
        except LastAdministratorError:
            return JsonResponse(
                {"error": "A workspace needs an active admin."}, status=400
            )
        return redirect("client-landing")


class WorkspaceMemberRoleView(WorkspaceAdminMixin, View):
    """Change an active company workspace member's role."""

    def post(self, request: HttpRequest, pk: int, membership_id: int):
        """Update a member role without allowing the last admin to be demoted."""
        workspace = self.get_workspace(pk)
        membership = get_object_or_404(
            WorkspaceMembership,
            pk=membership_id,
            workspace=workspace,
            is_active=True,
        )
        role = request.POST.get("role")
        valid_roles = {choice.value for choice in WorkspaceMembership.Role}
        if role not in valid_roles:
            return JsonResponse({"error": "Invalid workspace role."}, status=400)
        try:
            change_membership_role(membership, role)
        except LastAdministratorError:
            return JsonResponse(
                {"error": "A workspace needs an active admin."}, status=400
            )
        return redirect("workspace-members", pk=workspace.pk)


class WorkspaceInvitationAcceptView(ClientAccessMixin, View):
    """Accept a pending company workspace invitation."""

    def post(self, request: HttpRequest, pk: int):
        """Create client membership and consume the invitation atomically."""
        invitation = get_object_or_404(
            WorkspaceInvitation,
            pk=pk,
            invitee=request.user,
            status=WorkspaceInvitation.Status.PENDING,
            workspace__kind=Workspace.Kind.COMPANY,
        )
        with transaction.atomic():
            WorkspaceMembership.objects.update_or_create(
                workspace=invitation.workspace,
                user=request.user,
                defaults={
                    "role": WorkspaceMembership.Role.CLIENT,
                    "is_active": True,
                },
            )
            invitation.status = WorkspaceInvitation.Status.ACCEPTED
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["status", "accepted_at"])
        return redirect("client-landing")


class WorkspaceInvitationDeclineView(ClientAccessMixin, View):
    """Decline a pending company workspace invitation."""

    def post(self, request: HttpRequest, pk: int):
        """Mark the intended recipient's invitation as declined."""
        invitation = get_object_or_404(
            WorkspaceInvitation,
            pk=pk,
            invitee=request.user,
            status=WorkspaceInvitation.Status.PENDING,
        )
        invitation.status = WorkspaceInvitation.Status.DECLINED
        invitation.save(update_fields=["status"])
        return redirect("client-landing")


class WorkspaceInvitationRevokeView(WorkspaceAdminMixin, View):
    """Revoke a pending invitation from an administered company workspace."""

    def post(self, request: HttpRequest, pk: int, invitation_id: int):
        """Mark a pending workspace invitation as revoked."""
        workspace = self.get_workspace(pk)
        invitation = get_object_or_404(
            WorkspaceInvitation,
            pk=invitation_id,
            workspace=workspace,
            status=WorkspaceInvitation.Status.PENDING,
        )
        invitation.status = WorkspaceInvitation.Status.REVOKED
        invitation.save(update_fields=["status"])
        return redirect("client-landing")


class ClientProfileView(ClientAccessMixin, UpdateView):
    """Update personal fields for the authenticated client."""

    form_class = ClientProfileForm
    template_name = "core/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None) -> User:
        """Return only the currently authenticated user."""
        return self.request.user


class ClientPasswordChangeView(ClientAccessMixin, PasswordChangeView):
    """Change the password for the authenticated client."""

    form_class = PasswordChangeForm
    template_name = "core/password_change.html"
    success_url = reverse_lazy("profile")

    def get_form_kwargs(self) -> dict[str, object]:
        """Bind the password form to the authenticated user."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class PublicLandingPageView(TemplateView):
    """Render the public customer-facing product landing page."""

    template_name = "core/public_landing.html"


class ClientLandingPageView(ClientAccessMixin, TemplateView):
    """Render the authenticated client's task management landing page."""

    template_name = "core/client_landing.html"

    def get_projects(self) -> QuerySet[Project]:
        """Return projects owned by or shared with the authenticated client."""
        return (
            accessible_projects(self.request.user)
            .filter(
                Q(workspace__isnull=True) | Q(workspace__kind=Workspace.Kind.PERSONAL)
            )
            .annotate(task_count=Count("tasks"))
        )

    def get_tasks(self) -> QuerySet[Task]:
        """Return only tasks owned by the authenticated client."""
        return Task.objects.filter(client=self.request.user).filter(
            Q(project__workspace__isnull=True)
            | Q(project__workspace__kind=Workspace.Kind.PERSONAL)
        )

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Build task summary and task list data for the landing page."""
        context = super().get_context_data(**kwargs)
        tasks = self.get_tasks()
        status_counts = tasks.values("status").annotate(total=Count("id"))
        counts = {item["status"]: item["total"] for item in status_counts}
        context["projects"] = self.get_projects()
        context["pending_invitations"] = ProjectInvitation.objects.filter(
            invitee=self.request.user,
            status=ProjectInvitation.Status.PENDING,
        ).select_related("project", "inviter")
        context["pending_workspace_invitations"] = WorkspaceInvitation.objects.filter(
            invitee=self.request.user,
            status=WorkspaceInvitation.Status.PENDING,
        ).select_related("workspace", "inviter")
        context["company_workspaces"] = WorkspaceMembership.objects.filter(
            workspace__kind=Workspace.Kind.COMPANY,
            user=self.request.user,
            is_active=True,
        ).select_related("workspace")
        context["tasks"] = tasks
        context["task_lanes"] = build_task_lanes(tasks)
        context["task_statuses"] = Task.Status.choices
        context["task_view_label"] = "Task list"
        context["task_counts"] = {
            "outstanding": counts.get(Task.Status.OUTSTANDING, 0),
            "in_progress": counts.get(Task.Status.IN_PROGRESS, 0),
            "completed": counts.get(Task.Status.COMPLETED, 0),
        }
        return context


class ClientTaskCreateView(ClientAccessMixin, CreateView):
    """Create a task owned by the authenticated client."""

    model = Task
    form_class = TaskForm
    template_name = "core/task_form.html"
    success_url = reverse_lazy("client-landing")

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object):
        """Send clients to project creation until they have a project."""
        if not request.user.is_authenticated or not self.test_func():
            return super().dispatch(request, *args, **kwargs)
        if not accessible_projects(request.user).exists():
            return redirect("project-create")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, object]:
        """Limit selectable projects to those owned by the client."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["projects"] = accessible_projects(self.request.user)
        project_id = self.request.GET.get("project")
        if project_id:
            project = (
                accessible_projects(self.request.user).filter(pk=project_id).first()
            )
            if project is None:
                raise Http404
            kwargs["project_context"] = project
        return kwargs

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Expose project context for the create form presentation."""
        context = super().get_context_data(**kwargs)
        project_id = self.request.GET.get("project")
        context["project_context"] = (
            accessible_projects(self.request.user).filter(pk=project_id).first()
            if project_id
            else None
        )
        return context

    def form_valid(self, form: TaskForm):
        """Set task ownership from the authenticated user, never form data."""
        form.instance.client = form.cleaned_data["project"].client
        return super().form_valid(form)


class ClientTaskQuerysetMixin(ClientAccessMixin):
    """Limit task detail, update, and delete operations to task owners."""

    def get_queryset(self) -> QuerySet[Task]:
        """Return tasks owned by or shared with the authenticated client."""
        return Task.objects.filter(
            Q(client=self.request.user)
            | Q(
                project__memberships__user=self.request.user,
                project__memberships__is_active=True,
            )
            | Q(
                project__workspace__memberships__user=self.request.user,
                project__workspace__memberships__is_active=True,
            )
            | Q(project__client=self.request.user, client=F("project__client"))
        ).distinct()


class ClientTaskDetailView(ClientTaskQuerysetMixin, DetailView):
    """Display one task owned by the authenticated client."""

    model = Task
    template_name = "core/task_detail.html"


class ClientTaskUpdateView(ClientTaskQuerysetMixin, UpdateView):
    """Update one task owned by the authenticated client."""

    model = Task
    form_class = TaskForm
    template_name = "core/task_form.html"

    def get_form_kwargs(self) -> dict[str, object]:
        """Limit selectable projects to those owned by the client."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def get_success_url(self) -> str:
        """Return the updated task detail route."""
        return self.object.get_absolute_url()


class ClientTaskStatusView(ClientTaskQuerysetMixin, View):
    """Persist a status-lane move for an owned task."""

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Update only the requested task status and return its label."""
        task = self.get_queryset().filter(pk=pk).first()
        if task is None:
            raise Http404

        status = request.POST.get("status")
        valid_statuses = {choice.value: choice.label for choice in Task.Status}
        if status not in valid_statuses:
            return JsonResponse({"error": "Invalid task status."}, status=400)

        task.status = status
        task.save(update_fields=["status", "updated_at"])
        return JsonResponse({"status": status, "label": valid_statuses[status]})


class ClientTaskDeleteView(ClientTaskQuerysetMixin, DeleteView):
    """Delete one task owned by the authenticated client."""

    model = Task
    template_name = "core/task_confirm_delete.html"
    success_url = reverse_lazy("client-landing")

    def get_queryset(self) -> QuerySet[Task]:
        """Return only tasks owned by the authenticated client for deletion."""
        return (
            super()
            .get_queryset()
            .filter(
                Q(client=self.request.user)
                | Q(
                    project__workspace__memberships__user=self.request.user,
                    project__workspace__memberships__is_active=True,
                )
            )
            .distinct()
        )


class ClientProjectQuerysetMixin(ClientAccessMixin):
    """Limit project views to projects owned by the authenticated client."""

    def get_queryset(self) -> QuerySet[Project]:
        """Return projects owned by or shared with the authenticated client."""
        return accessible_projects(self.request.user).annotate(
            task_count=Count("tasks")
        )


def accessible_projects(user: User) -> QuerySet[Project]:
    """Return projects owned by or shared with the authenticated user."""
    return Project.objects.filter(
        Q(client=user)
        | Q(memberships__user=user, memberships__is_active=True)
        | Q(workspace__memberships__user=user, workspace__memberships__is_active=True)
    ).distinct()


def project_workspaces(user: User) -> QuerySet[Workspace]:
    """Return personal workspaces and company workspaces administered by a user."""
    return Workspace.objects.filter(
        Q(
            kind=Workspace.Kind.PERSONAL,
            memberships__user=user,
            memberships__is_active=True,
        )
        | Q(
            kind=Workspace.Kind.COMPANY,
            memberships__user=user,
            memberships__role=WorkspaceMembership.Role.ADMIN,
            memberships__is_active=True,
        )
    ).distinct()


class ClientProjectOwnerMixin(ClientAccessMixin):
    """Restrict project management to owners and workspace administrators."""

    def get_queryset(self) -> QuerySet[Project]:
        """Return projects owned by or administered by the current user."""
        return Project.objects.filter(
            Q(client=self.request.user)
            | Q(
                workspace__memberships__user=self.request.user,
                workspace__memberships__role=WorkspaceMembership.Role.ADMIN,
                workspace__memberships__is_active=True,
            )
        ).distinct()


class ClientProjectListView(ClientProjectQuerysetMixin, TemplateView):
    """Display the authenticated client's projects."""

    template_name = "core/project_list.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add the client's projects to the page context."""
        context = super().get_context_data(**kwargs)
        context["projects"] = self.get_queryset()
        return context


class ClientProjectCreateView(ClientAccessMixin, CreateView):
    """Create a project in an accessible personal or company workspace."""

    model = Project
    form_class = ProjectForm
    template_name = "core/project_form.html"

    def get_form_kwargs(self) -> dict[str, object]:
        """Pass the authenticated client and writable workspaces to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["workspaces"] = project_workspaces(self.request.user)
        return kwargs

    def form_valid(self, form):
        """Set project ownership and preserve a personal fallback for legacy users."""
        form.instance.client = self.request.user
        if form.cleaned_data.get("workspace") is None:
            form.instance.workspace = (
                project_workspaces(self.request.user)
                .filter(kind=Workspace.Kind.PERSONAL)
                .first()
            )
        return super().form_valid(form)


class ClientProjectDetailView(ClientProjectQuerysetMixin, DetailView):
    """Display one project and its owned tasks."""

    model = Project
    template_name = "core/project_detail.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        """Add stable status lanes for this project's tasks."""
        context = super().get_context_data(**kwargs)
        tasks = list(self.object.tasks.all())
        context["tasks"] = tasks
        context["task_lanes"] = build_task_lanes(tasks)
        context["task_statuses"] = Task.Status.choices
        context["task_view_label"] = "Project tasks"
        context["is_project_owner"] = self.object.client_id == self.request.user.id
        return context


class ClientProjectUpdateView(ClientProjectOwnerMixin, UpdateView):
    """Update a project owned by the authenticated client."""

    model = Project
    form_class = ProjectForm
    template_name = "core/project_form.html"

    def get_form_kwargs(self) -> dict[str, object]:
        """Pass the authenticated client and writable workspaces to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user
        kwargs["workspaces"] = project_workspaces(self.request.user)
        return kwargs


class ClientProjectDeleteView(ClientProjectOwnerMixin, DeleteView):
    """Delete a project owned by the authenticated client."""

    model = Project
    template_name = "core/project_confirm_delete.html"
    success_url = reverse_lazy("project-list")


class ClientProjectInviteView(ClientProjectOwnerMixin, View):
    """Invite and list Client collaborators for an owned project."""

    def get(self, request: HttpRequest, pk: int):
        """Render the owner invitation form and current membership states."""
        project = get_object_or_404(self.get_queryset(), pk=pk)
        workspace = project.workspace
        return render(
            request,
            "core/project_collaborators.html",
            {
                "project": project,
                "workspace": (
                    workspace
                    if workspace and workspace.kind == Workspace.Kind.COMPANY
                    else None
                ),
                "membership": (
                    workspace.memberships.filter(user=request.user).first()
                    if workspace and workspace.kind == Workspace.Kind.COMPANY
                    else None
                ),
                "form": ProjectInviteForm(project=project, inviter=request.user),
                "invitations": project.invitations.select_related("invitee"),
                "memberships": project.memberships.filter(
                    is_active=True
                ).select_related("user"),
            },
        )

    def post(self, request: HttpRequest, pk: int):
        """Create a pending invitation for an eligible Client user."""
        project = get_object_or_404(self.get_queryset(), pk=pk)
        form = ProjectInviteForm(request.POST, project=project, inviter=request.user)
        if form.is_valid():
            ProjectInvitation.objects.create(
                project=project, inviter=request.user, invitee=form.invitee
            )
            return redirect(project.get_absolute_url())
        workspace = project.workspace
        return render(
            request,
            "core/project_collaborators.html",
            {
                "project": project,
                "workspace": (
                    workspace
                    if workspace and workspace.kind == Workspace.Kind.COMPANY
                    else None
                ),
                "membership": (
                    workspace.memberships.filter(user=request.user).first()
                    if workspace and workspace.kind == Workspace.Kind.COMPANY
                    else None
                ),
                "form": form,
                "invitations": [],
                "memberships": [],
            },
        )


class ClientProjectInviteSuggestionsView(ClientProjectOwnerMixin, View):
    """Return eligible Client usernames for an owner's invite combobox."""

    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Return a small, privacy-filtered username result set."""
        project = get_object_or_404(self.get_queryset(), pk=pk)
        query = request.GET.get("q", "").strip()
        if query.startswith("@"):
            query = query[1:]

        active_ids = ProjectMembership.objects.filter(
            project=project, is_active=True
        ).values("user_id")
        pending_ids = ProjectInvitation.objects.filter(
            project=project, status=ProjectInvitation.Status.PENDING
        ).values("invitee_id")
        results = (
            User.objects.filter(groups__name="Client", username__icontains=query)
            .exclude(pk=request.user.pk)
            .exclude(pk__in=active_ids)
            .exclude(pk__in=pending_ids)
            .order_by("username")
            .values("username")[:10]
        )
        return JsonResponse({"results": list(results)})


class ClientProjectInvitationAcceptView(ClientAccessMixin, View):
    """Accept a pending invitation for its intended Client recipient."""

    def get(self, request: HttpRequest, token):
        """Render the pending invitation confirmation for its recipient."""
        invitation = self._get_invitation(request, token)
        return render(
            request, "core/project_invitation.html", {"invitation": invitation}
        )

    def post(self, request: HttpRequest, token):
        """Activate membership and consume the invitation token."""
        invitation = self._get_invitation(request, token)
        ProjectMembership.objects.update_or_create(
            project=invitation.project,
            user=request.user,
            defaults={"is_active": True},
        )
        invitation.status = ProjectInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at"])
        return redirect(invitation.project.get_absolute_url())

    def _get_invitation(self, request: HttpRequest, token) -> ProjectInvitation:
        """Return a pending invitation only to its intended recipient."""
        invitation = (
            ProjectInvitation.objects.filter(
                token=token,
                invitee=request.user,
                status=ProjectInvitation.Status.PENDING,
            )
            .select_related("project", "inviter")
            .first()
        )
        if invitation is None:
            raise Http404
        return invitation


class ClientProjectInvitationReviewView(ClientAccessMixin, View):
    """Render a pending invitation without exposing its token in the inbox."""

    def get(self, request: HttpRequest, pk: int):
        """Show a recipient's pending invitation confirmation page."""
        invitation = get_object_or_404(
            ProjectInvitation.objects.select_related("project", "inviter"),
            pk=pk,
            invitee=request.user,
            status=ProjectInvitation.Status.PENDING,
        )
        return render(
            request, "core/project_invitation.html", {"invitation": invitation}
        )


class ClientProjectInvitationAcceptByIdView(ClientAccessMixin, View):
    """Accept a pending invitation from the recipient inbox flow."""

    def post(self, request: HttpRequest, pk: int):
        """Activate membership for the intended recipient."""
        invitation = get_object_or_404(
            ProjectInvitation,
            pk=pk,
            invitee=request.user,
            status=ProjectInvitation.Status.PENDING,
        )
        ProjectMembership.objects.update_or_create(
            project=invitation.project,
            user=request.user,
            defaults={"is_active": True},
        )
        invitation.status = ProjectInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at"])
        return redirect(invitation.project.get_absolute_url())


class ClientProjectInvitationDeclineByIdView(ClientAccessMixin, View):
    """Decline a pending invitation from the recipient inbox flow."""

    def post(self, request: HttpRequest, pk: int):
        """Mark the intended recipient's invitation as declined."""
        invitation = get_object_or_404(
            ProjectInvitation,
            pk=pk,
            invitee=request.user,
            status=ProjectInvitation.Status.PENDING,
        )
        invitation.status = ProjectInvitation.Status.DECLINED
        invitation.save(update_fields=["status"])
        return redirect("client-landing")


class ClientProjectInvitationDeclineView(ClientAccessMixin, View):
    """Decline a pending invitation for its intended recipient."""

    def post(self, request: HttpRequest, token):
        """Mark the recipient's pending invitation as declined."""
        invitation = ProjectInvitation.objects.filter(
            token=token, invitee=request.user, status=ProjectInvitation.Status.PENDING
        ).first()
        if invitation is None:
            raise Http404
        invitation.status = ProjectInvitation.Status.DECLINED
        invitation.save(update_fields=["status"])
        return redirect("client-landing")


class ClientProjectInvitationRevokeView(ClientProjectOwnerMixin, View):
    """Revoke a pending invitation owned by the current project owner."""

    def post(self, request: HttpRequest, pk: int, invitation_id: int):
        """Mark a pending invitation as revoked."""
        project = get_object_or_404(self.get_queryset(), pk=pk)
        invitation = get_object_or_404(
            ProjectInvitation,
            pk=invitation_id,
            project=project,
            status=ProjectInvitation.Status.PENDING,
        )
        invitation.status = ProjectInvitation.Status.REVOKED
        invitation.save(update_fields=["status"])
        return redirect("project-invite", pk=project.pk)


class ClientProjectMemberRemoveView(ClientProjectOwnerMixin, View):
    """Remove an active collaborator without deleting project data."""

    def post(self, request: HttpRequest, pk: int, membership_id: int):
        """Deactivate an active project membership."""
        project = get_object_or_404(self.get_queryset(), pk=pk)
        membership = get_object_or_404(
            ProjectMembership,
            pk=membership_id,
            project=project,
            is_active=True,
        )
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return redirect("project-invite", pk=project.pk)


class HealthCheckView(View):
    """Return a small response that confirms the application is running."""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Return the current application health status."""
        return JsonResponse({"status": "ok"})
