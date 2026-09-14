from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.test import Client as TestClient
from django.test import TestCase

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


class HealthCheckViewTests(TestCase):
    """Verify that the initial application health endpoint is available."""

    def test_health_check_returns_ok(self) -> None:
        """The health endpoint returns a successful JSON response."""
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})


class PublicLandingPageTests(TestCase):
    """Verify public landing access and navigation to authentication."""

    def test_anonymous_users_can_view_public_landing(self) -> None:
        """Anonymous visitors see product information and auth actions."""
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client tasks")
        self.assertContains(response, "Sign in")
        self.assertContains(response, "Create an account")
        self.assertContains(response, "Project-based task management")
        self.assertContains(response, "Ready to work together?")
        for feature in (
            "Personal client workspace",
            "Status lanes and list view",
            "Project invitations",
            "Company workspaces",
            "Workspace invitations",
            "role-aware access",
        ):
            with self.subTest(feature=feature):
                self.assertContains(response, feature)
        self.assertNotContains(response, "AI agents")
        self.assertNotContains(response, "file uploads")
        self.assertContains(response, "Client tasks")

    def test_authenticated_users_can_continue_to_workspace(self) -> None:
        """Authenticated users can reach the protected workspace from public entry."""
        client_group = Group.objects.create(name="Client")
        user = User.objects.create_user(username="landing-client", password="password")
        user.groups.add(client_group)
        self.client.force_login(user)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open workspace")
        self.assertContains(response, "personal client overview")
        self.assertContains(response, "/workspace/")

    def test_workspace_requires_client_access(self) -> None:
        """The authenticated workspace remains protected at its stable route."""
        response = self.client.get("/workspace/")

        self.assertRedirects(response, "/accounts/login/?next=/workspace/")


class AuthenticatedNavigationTests(TestCase):
    """Verify shared profile and workspace navigation menu contracts."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.user = User.objects.create_user(
            username="navigation-client", password="test-password"
        )
        self.user.groups.add(self.client_group)
        self.client.force_login(self.user)

    def test_client_overview_exposes_profile_menu_and_csrf_logout(self) -> None:
        """The client header groups profile and sign-out actions in a menu."""
        response = self.client.get("/workspace/")

        self.assertContains(response, 'aria-label="Open account menu"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, 'aria-controls="account-menu"')
        self.assertContains(response, 'id="account-menu"')
        self.assertContains(response, 'href="/profile/"')
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, "navigation_menu.js")
        self.assertGreater(
            response.content.find(b'data-menu-trigger="account-menu"'),
            response.content.find(b'class="brand"'),
        )

    def test_company_workspace_menu_contains_contextual_links(self) -> None:
        """An active workspace exposes scoped destinations through its menu."""
        workspace = Workspace.objects.create(
            name="Navigation Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.user,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.get(f"/workspaces/{workspace.pk}/")

        self.assertContains(response, 'aria-label="Workspace menu"')
        self.assertContains(response, 'aria-controls="workspace-menu"')
        header_end = response.content.find(b"</header>")
        self.assertNotIn(
            b'class="workspace-menu-trigger"', response.content[:header_end]
        )
        main_start = response.content.find(b"<main>")
        self.assertGreater(
            response.content.find(b'aria-label="Workspace menu"'), main_start
        )
        self.assertContains(response, workspace.name)
        self.assertContains(response, f"/workspaces/{workspace.pk}/projects/")
        self.assertContains(response, f"/workspaces/{workspace.pk}/tasks/")
        self.assertContains(response, f"/workspaces/{workspace.pk}/members/")
        self.assertContains(response, f"/workspaces/{workspace.pk}/settings/")
        self.assertContains(response, "/workspace/")

    def test_company_client_does_not_see_workspace_settings_menu_item(self) -> None:
        """Clients do not receive administrator-only workspace settings navigation."""
        workspace = Workspace.objects.create(
            name="Client Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.user,
            role=WorkspaceMembership.Role.CLIENT,
        )

        response = self.client.get(f"/workspaces/{workspace.pk}/")

        self.assertNotContains(response, f"/workspaces/{workspace.pk}/settings/")

    def test_workspace_action_pages_use_shared_headers_and_menu(self) -> None:
        """Workspace action pages retain both shared navigation contexts."""
        workspace = Workspace.objects.create(
            name="Action Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.user,
            role=WorkspaceMembership.Role.ADMIN,
        )
        project = Project.objects.create(
            client=self.user, workspace=workspace, name="Action project"
        )
        task = Task.objects.create(
            client=self.user, project=project, title="Action task"
        )
        paths = (
            f"/workspaces/{workspace.pk}/projects/new/",
            f"/workspaces/{workspace.pk}/tasks/new/",
            f"/workspaces/{workspace.pk}/settings/",
            f"/workspaces/{workspace.pk}/tasks/{task.pk}/",
        )

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Open account menu"')
                self.assertContains(response, 'aria-label="Workspace menu"')

        collaborator_response = self.client.get(
            f"/projects/{project.pk}/collaborators/invite/"
        )
        self.assertContains(collaborator_response, 'aria-label="Open account menu"')
        self.assertContains(collaborator_response, 'aria-label="Workspace menu"')

    def test_workspace_delete_and_project_collaboration_pages_use_shared_menus(
        self,
    ) -> None:
        """Destructive and collaboration pages keep shared navigation context."""
        workspace = Workspace.objects.create(
            name="Navigation Actions", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.user,
            role=WorkspaceMembership.Role.ADMIN,
        )
        project = Project.objects.create(
            client=self.user, workspace=workspace, name="Navigation project"
        )
        task = Task.objects.create(
            client=self.user, project=project, title="Navigation task"
        )
        response = self.client.get(
            f"/workspaces/{workspace.pk}/tasks/{task.pk}/delete/"
        )

        self.assertContains(response, 'aria-label="Open account menu"')
        self.assertContains(response, 'aria-label="Workspace menu"')

    def test_authenticated_pages_use_shared_profile_menu(self) -> None:
        """Personal and workspace pages expose the shared account menu trigger."""
        project = Project.objects.create(client=self.user, name="Navigation project")
        task = Task.objects.create(
            client=self.user, project=project, title="Navigation task"
        )
        paths = (
            "/projects/",
            f"/projects/{project.pk}/",
            f"/projects/{project.pk}/edit/",
            "/tasks/new/",
            f"/tasks/{task.pk}/",
        )

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Open account menu"')
                self.assertContains(response, 'id="account-menu"')


class ClientProfileTests(TestCase):
    """Verify client profile access and privilege boundaries."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.user = User.objects.create_user(
            username="profile-client", password="old-password"
        )
        self.user.groups.add(self.client_group)
        self.other_user = User.objects.create_user(
            username="profile-other", password="other-password"
        )
        self.client.force_login(self.user)

    def test_client_can_update_personal_profile_fields(self) -> None:
        """A client can save approved personal fields."""
        response = self.client.post(
            "/profile/",
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
            },
        )

        self.assertRedirects(response, "/profile/")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ada")
        self.assertEqual(self.user.last_name, "Lovelace")
        self.assertEqual(self.user.email, "ada@example.com")

    def test_profile_payload_cannot_change_authorization(self) -> None:
        """Unauthorized user fields are ignored by the profile form."""
        self.client.post(
            "/profile/",
            {
                "first_name": "Safe",
                "username": "hijacked",
                "is_staff": "on",
                "is_superuser": "on",
                "groups": [self.client_group.pk],
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile-client")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.groups.filter(name="Client").exists())

    def test_anonymous_and_non_client_profile_access_is_denied(self) -> None:
        """Only client users can access profile pages."""
        self.client.logout()
        self.assertRedirects(
            self.client.get("/profile/"), "/accounts/login/?next=/profile/"
        )
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get("/profile/").status_code, 403)

    def test_password_change_requires_current_password(self) -> None:
        """Password changes use Django validation and invalidate old credentials."""
        response = self.client.post(
            "/profile/password/",
            {
                "old_password": "old-password",
                "new_password1": "new-secure-password",
                "new_password2": "new-secure-password",
            },
        )

        self.assertRedirects(response, "/profile/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-secure-password"))
        self.assertFalse(self.user.check_password("old-password"))

    def test_password_change_rejects_wrong_current_password(self) -> None:
        """An incorrect current password leaves the account unchanged."""
        response = self.client.post(
            "/profile/password/",
            {
                "old_password": "wrong-password",
                "new_password1": "new-secure-password",
                "new_password2": "new-secure-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password"))


class ClientRegistrationTests(TestCase):
    """Verify secure registration and automatic client authorization."""

    def test_registration_page_is_public(self) -> None:
        """Anonymous users can open the registration form."""
        response = self.client.get("/accounts/register/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_successful_registration_creates_client_user(self) -> None:
        """Valid registration creates a regular user in the Client group."""
        response = self.client.post(
            "/accounts/register/",
            {
                "username": "new-client",
                "email": "new-client@example.com",
                "password1": "secure-registration-password",
                "password2": "secure-registration-password",
            },
        )

        self.assertRedirects(response, "/accounts/login/")
        user = User.objects.get(username="new-client")
        self.assertTrue(user.check_password("secure-registration-password"))
        self.assertTrue(user.groups.filter(name="Client").exists())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(
            Workspace.objects.filter(
                kind=Workspace.Kind.PERSONAL,
                memberships__user=user,
                memberships__role=WorkspaceMembership.Role.ADMIN,
            ).exists()
        )

    def test_invalid_registration_does_not_create_user(self) -> None:
        """Invalid passwords re-render errors without creating a user."""
        response = self.client.post(
            "/accounts/register/",
            {
                "username": "invalid-client",
                "email": "invalid@example.com",
                "password1": "short",
                "password2": "different",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password")
        self.assertFalse(User.objects.filter(username="invalid-client").exists())

    def test_duplicate_username_is_rejected(self) -> None:
        """A duplicate username is rejected without creating another user."""
        User.objects.create_user(username="existing-client", password="password")

        response = self.client.post(
            "/accounts/register/",
            {
                "username": "existing-client",
                "email": "new@example.com",
                "password1": "secure-registration-password",
                "password2": "secure-registration-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists")
        self.assertEqual(User.objects.filter(username="existing-client").count(), 1)

    def test_registration_cannot_grant_elevated_privileges(self) -> None:
        """Privilege fields in submitted data are ignored by the form."""
        self.client.post(
            "/accounts/register/",
            {
                "username": "regular-client",
                "email": "regular@example.com",
                "password1": "secure-registration-password",
                "password2": "secure-registration-password",
                "is_staff": "on",
                "is_superuser": "on",
            },
        )

        user = User.objects.get(username="regular-client")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class ClientLandingPageTests(TestCase):
    """Verify authentication and client isolation on the landing page."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.client_user = User.objects.create_user(
            username="client@example.com", password="test-password"
        )
        self.client_user.groups.add(self.client_group)
        self.project = Project.objects.create(
            client=self.client_user, name="Client project"
        )
        self.other_user = User.objects.create_user(
            username="other@example.com", password="test-password"
        )
        self.other_project = Project.objects.create(
            client=self.other_user, name="Other project"
        )

    def test_anonymous_users_are_redirected_to_login_for_workspace(self) -> None:
        """Anonymous users cannot access the protected workspace."""
        response = self.client.get("/workspace/")

        self.assertRedirects(response, "/accounts/login/?next=/workspace/")

    def test_client_login_redirects_to_landing_page(self) -> None:
        """A client who signs in is sent to the client landing page."""
        response = self.client.post(
            "/accounts/login/",
            {"username": "client@example.com", "password": "test-password"},
        )

        self.assertRedirects(response, "/workspace/")

    def test_authenticated_non_client_is_forbidden(self) -> None:
        """An authenticated user outside the Client group is denied."""
        self.client.force_login(self.other_user)

        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, 403)

    def test_staff_status_does_not_grant_client_access(self) -> None:
        """Staff status alone does not bypass the client boundary."""
        self.other_user.is_staff = True
        self.other_user.save(update_fields=["is_staff"])
        self.client.force_login(self.other_user)

        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, 403)

    def test_landing_page_shows_only_authenticated_client_tasks(self) -> None:
        """A client sees its own task summary and not another client's task."""
        own_task = Task.objects.create(
            client=self.client_user,
            project=self.project,
            title="Review project brief",
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.HIGH,
        )
        Task.objects.create(
            client=self.other_user,
            project=self.other_project,
            title="Private task",
        )
        self.client.force_login(self.client_user)

        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_task.title)
        self.assertNotContains(response, "Private task")
        self.assertEqual(response.context["task_counts"]["in_progress"], 1)

    def test_landing_page_defaults_to_status_lanes_with_list_fallback(self) -> None:
        """The workspace exposes default lanes and the current list view."""
        self.client.force_login(self.client_user)
        Task.objects.create(
            client=self.client_user,
            project=self.project,
            title="Lane task",
            status=Task.Status.COMPLETED,
        )

        response = self.client.get("/workspace/")

        self.assertContains(response, 'data-task-view="lanes"')
        self.assertContains(response, 'data-task-view-panel="lanes"')
        self.assertContains(response, 'data-task-view-panel="list"')
        self.assertContains(response, "Outstanding")
        self.assertContains(response, "In progress")
        self.assertContains(response, "Completed")
        self.assertContains(response, "Move to")

    def test_landing_page_shows_empty_state_without_tasks(self) -> None:
        """A client without tasks receives a useful empty state."""
        self.client.force_login(self.client_user)

        response = self.client.get("/workspace/")

        self.assertContains(response, "No tasks yet")


class ClientTaskManagementTests(TestCase):
    """Verify client-owned task CRUD and request protection."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.client_user = User.objects.create_user(
            username="task-client@example.com", password="test-password"
        )
        self.client_user.groups.add(self.client_group)
        self.project = Project.objects.create(
            client=self.client_user, name="Task project"
        )
        self.other_user = User.objects.create_user(
            username="task-other@example.com", password="test-password"
        )
        self.task = Task.objects.create(
            client=self.client_user,
            project=self.project,
            title="Review project brief",
            status=Task.Status.OUTSTANDING,
            priority=Task.Priority.MEDIUM,
        )
        self.client.force_login(self.client_user)

    def test_client_can_create_task(self) -> None:
        """A valid task is assigned to the authenticated client."""
        response = self.client.post(
            "/tasks/new/",
            {
                "title": "Prepare project notes",
                "description": "<p>Important <strong>project</strong> notes.</p>",
                "project": self.project.pk,
                "status": Task.Status.IN_PROGRESS,
                "priority": Task.Priority.HIGH,
                "due_date": "2026-10-01",
            },
        )

        created_task = Task.objects.get(title="Prepare project notes")
        self.assertRedirects(response, "/workspace/")
        self.assertEqual(created_task.client, self.client_user)
        self.assertEqual(
            created_task.description, "<p>Important <strong>project</strong> notes.</p>"
        )

    def test_project_context_prefills_task_create(self) -> None:
        """Project-scoped creation associates the task with the URL project."""
        response = self.client.get(f"/tasks/new/?project={self.project.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project_context"], self.project)
        self.assertContains(response, self.project.name)

        response = self.client.post(
            f"/tasks/new/?project={self.project.pk}",
            {
                "title": "Contextual task",
                "project": self.project.pk,
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
            },
        )

        self.assertRedirects(response, "/workspace/")
        self.assertTrue(
            Task.objects.filter(title="Contextual task", project=self.project).exists()
        )

    def test_task_edit_keeps_project_selector_available(self) -> None:
        """Editing a task keeps the project field editable."""
        response = self.client.get(f"/tasks/{self.task.pk}/edit/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="project"')
        self.assertContains(response, self.project.name)

    def test_task_description_sanitizes_unsafe_html(self) -> None:
        """Task descriptions preserve formatting without executable markup."""
        response = self.client.post(
            "/tasks/new/",
            {
                "project": self.project.pk,
                "title": "Safe task",
                "description": (
                    '<p>Safe</p><script>alert("x")</script>'
                    '<a href="javascript:bad">bad</a>'
                ),
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
            },
        )

        self.assertRedirects(response, "/workspace/")
        task = Task.objects.get(title="Safe task")
        self.assertNotIn("script", task.description.lower())
        self.assertNotIn("javascript:", task.description.lower())
        self.assertContains(self.client.get(task.get_absolute_url()), "Safe")

    def test_task_without_description_shows_empty_state(self) -> None:
        """Tasks without descriptions render a clear empty state."""
        response = self.client.get(self.task.get_absolute_url())

        self.assertContains(response, "No description added yet")

    def test_invalid_task_does_not_create_record(self) -> None:
        """An invalid task form is shown without creating a task."""
        response = self.client.post(
            "/tasks/new/",
            {
                "title": "",
                "project": self.project.pk,
                "status": "invalid",
                "priority": Task.Priority.HIGH,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Task.objects.count(), 1)

    def test_client_can_view_and_update_owned_task(self) -> None:
        """An owner can view and update its task."""
        detail_response = self.client.get(self.task.get_absolute_url())
        update_response = self.client.post(
            f"/tasks/{self.task.pk}/edit/",
            {
                "title": "Updated brief",
                "project": self.project.pk,
                "status": Task.Status.COMPLETED,
                "priority": Task.Priority.LOW,
                "due_date": "",
            },
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, self.task.title)
        self.assertRedirects(update_response, self.task.get_absolute_url())
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated brief")
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_client_can_move_owned_task_between_statuses(self) -> None:
        """An owner can persist a status-lane move without changing task data."""
        response = self.client.post(
            f"/tasks/{self.task.pk}/status/",
            {"status": Task.Status.IN_PROGRESS},
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": Task.Status.IN_PROGRESS, "label": "In progress"},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)
        self.assertEqual(self.task.title, "Review project brief")
        self.assertEqual(self.task.project, self.project)
        self.assertEqual(self.task.priority, Task.Priority.MEDIUM)

    def test_task_status_move_rejects_invalid_status(self) -> None:
        """Invalid lane values do not change the task status."""
        response = self.client.post(
            f"/tasks/{self.task.pk}/status/", {"status": "not-a-status"}
        )

        self.assertEqual(response.status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.OUTSTANDING)

    def test_other_client_cannot_move_owned_task(self) -> None:
        """A client cannot move another client's task by identifier."""
        self.task.client = self.other_user
        self.task.save(update_fields=["client"])

        response = self.client.post(
            f"/tasks/{self.task.pk}/status/", {"status": Task.Status.COMPLETED}
        )

        self.assertEqual(response.status_code, 404)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.OUTSTANDING)

    def test_client_can_delete_owned_task(self) -> None:
        """An owner can confirm and delete its task."""
        confirm_response = self.client.get(f"/tasks/{self.task.pk}/delete/")
        delete_response = self.client.post(f"/tasks/{self.task.pk}/delete/", {})

        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Delete")
        self.assertRedirects(delete_response, "/workspace/")
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_other_client_cannot_access_owned_task(self) -> None:
        """Another client cannot read, update, or delete the task."""
        self.task.client = self.other_user
        self.task.save(update_fields=["client"])

        for path in (
            self.task.get_absolute_url(),
            f"/tasks/{self.task.pk}/edit/",
            f"/tasks/{self.task.pk}/delete/",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)

        response = self.client.post(
            f"/tasks/{self.task.pk}/edit/",
            {"title": "Attempted takeover", "status": Task.Status.COMPLETED},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_task_mutations_require_csrf(self) -> None:
        """State-changing task requests reject missing CSRF tokens."""
        csrf_client = TestClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.client_user)

        response = csrf_client.post(
            "/tasks/new/",
            {
                "title": "Missing token",
                "project": self.project.pk,
                "status": Task.Status.OUTSTANDING,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Task.objects.filter(title="Missing token").exists())


class ClientProjectManagementTests(TestCase):
    """Verify project ownership and project-first task creation."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.client_user = User.objects.create_user(
            username="project-client@example.com", password="test-password"
        )
        self.client_user.groups.add(self.client_group)
        self.other_user = User.objects.create_user(
            username="project-other@example.com", password="test-password"
        )
        self.other_project = Project.objects.create(
            client=self.other_user, name="Private project"
        )
        self.client.force_login(self.client_user)

    def test_client_can_create_and_view_project(self) -> None:
        """A client can create a project and see it in the project list."""
        response = self.client.post(
            "/projects/new/",
            {"name": "Website refresh", "description": "Public site work"},
        )

        project = Project.objects.get(name="Website refresh")
        self.assertRedirects(response, project.get_absolute_url())
        self.assertContains(self.client.get("/projects/"), project.name)

    def test_project_detail_defaults_to_status_lanes_with_list_fallback(self) -> None:
        """Project tasks expose the same lane and list presentation controls."""
        task = Task.objects.create(
            client=self.client_user,
            project=Project.objects.create(
                client=self.client_user, name="Lane project"
            ),
            title="Lane task",
        )

        response = self.client.get(task.project.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-task-view="lanes"')
        self.assertContains(response, 'data-task-view-panel="list"')
        self.assertContains(response, "Lane task")
        self.assertContains(response, "Move to")
        self.assertContains(response, 'option value="completed"')

    def test_project_pages_use_the_full_width_layout_hook(self) -> None:
        """Project pages expose the layout hook that expands their content area."""
        project = Project.objects.create(client=self.client_user, name="Workspace")

        project_list_response = self.client.get("/projects/")
        project_detail_response = self.client.get(project.get_absolute_url())

        self.assertContains(project_list_response, 'class="detail-panel project-page"')
        self.assertContains(
            project_detail_response, 'class="detail-panel project-page"'
        )

    def test_project_and_task_action_pages_show_workspace_navigation(self) -> None:
        """Project and task action pages render the shared workspace navigation."""
        project = Project.objects.create(client=self.client_user, name="Workspace")
        task = Task.objects.create(
            client=self.client_user, project=project, title="Review navigation"
        )
        action_paths = (
            "/projects/new/",
            f"/projects/{project.pk}/edit/",
            f"/projects/{project.pk}/delete/",
            "/tasks/new/",
            f"/tasks/{task.pk}/edit/",
            f"/tasks/{task.pk}/delete/",
        )

        for path in action_paths:
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "authenticated-topbar")
                self.assertContains(response, 'class="brand"')
                self.assertContains(response, 'action="/accounts/logout/"')
                self.assertContains(response, 'aria-label="Open account menu"')

    def test_project_name_is_unique_per_client(self) -> None:
        """A client cannot create duplicate project names."""
        Project.objects.create(client=self.client_user, name="Website refresh")

        response = self.client.post(
            "/projects/new/", {"name": "Website refresh", "description": "Again"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Project.objects.filter(
                client=self.client_user, name="Website refresh"
            ).count(),
            1,
        )
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'aria-describedby="id_name-error"')
        self.assertContains(response, 'id="id_name-error"')
        self.assertContains(response, "form_validation.js")

    def test_client_cannot_access_other_clients_project(self) -> None:
        """Project detail, edit, and delete are owner-scoped."""
        for path in (
            self.other_project.get_absolute_url(),
            f"/projects/{self.other_project.pk}/edit/",
            f"/projects/{self.other_project.pk}/delete/",
        ):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_task_creation_requires_a_project(self) -> None:
        """A client must choose a project before a task can be created."""
        Project.objects.create(client=self.client_user, name="Available project")
        response = self.client.post(
            "/tasks/new/",
            {
                "title": "Unassigned task",
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertFalse(Task.objects.filter(title="Unassigned task").exists())

    def test_task_creation_redirects_when_client_has_no_projects(self) -> None:
        """A client must create a project before opening task creation."""
        self.client_user.client_projects.all().delete()

        response = self.client.get("/tasks/new/")

        self.assertRedirects(response, "/projects/new/")

    def test_anonymous_task_creation_redirects_to_login(self) -> None:
        """Anonymous users follow the login flow instead of raising an error."""
        self.client.logout()

        response = self.client.get("/tasks/new/")

        self.assertRedirects(response, "/accounts/login/?next=/tasks/new/")

    def test_non_client_task_creation_is_forbidden(self) -> None:
        """Authenticated users outside Client cannot create tasks."""
        self.client.force_login(self.other_user)

        response = self.client.get("/tasks/new/")

        self.assertEqual(response.status_code, 403)


class ProjectCollaborationTests(TestCase):
    """Verify project invitation lifecycle and collaborator boundaries."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.owner = User.objects.create_user(
            username="owner@example.com", password="test-password"
        )
        self.owner.groups.add(self.client_group)
        self.invitee = User.objects.create_user(
            username="invitee@example.com", password="test-password"
        )
        self.invitee.groups.add(self.client_group)
        self.outsider = User.objects.create_user(
            username="outsider@example.com", password="test-password"
        )
        self.project = Project.objects.create(client=self.owner, name="Shared project")
        self.task = Task.objects.create(
            client=self.owner, project=self.project, title="Shared task"
        )
        self.client.force_login(self.owner)

    def test_owner_can_invite_client_and_invitee_can_accept(self) -> None:
        """An owner can create an invitation that only its recipient accepts."""
        response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/invite/",
            {"username": self.invitee.username},
        )

        self.assertRedirects(response, self.project.get_absolute_url())
        invitation = ProjectInvitation.objects.get(project=self.project)
        self.assertEqual(invitation.invitee, self.invitee)
        self.assertTrue(invitation.is_pending)

        self.client.force_login(self.invitee)
        response = self.client.post(f"/invitations/{invitation.token}/accept/")

        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertTrue(
            ProjectMembership.objects.filter(
                project=self.project, user=self.invitee, is_active=True
            ).exists()
        )
        self.assertEqual(
            self.client.get(self.project.get_absolute_url()).status_code, 200
        )
        self.assertEqual(self.client.get(self.task.get_absolute_url()).status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.ACCEPTED)
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(
            ProjectMembership.objects.filter(
                project=self.project, user=self.invitee, is_active=True
            ).count(),
            1,
        )

    def test_collaborator_cannot_manage_project_or_invite_users(self) -> None:
        """Collaborators can work in a project but cannot manage ownership controls."""
        membership = ProjectMembership.objects.create(
            project=self.project, user=self.invitee
        )
        self.client.force_login(self.invitee)

        self.assertEqual(
            self.client.get(f"/projects/{self.project.pk}/edit/").status_code, 404
        )
        response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/invite/",
            {"username": self.outsider.username},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.get(f"/tasks/{self.task.pk}/delete/").status_code, 404
        )
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

    def test_non_client_and_duplicate_invites_are_rejected(self) -> None:
        """Invites reject non-clients and duplicate pending invitations."""
        first_response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/invite/",
            {"username": self.invitee.username},
        )
        duplicate_response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/invite/",
            {"username": self.invitee.username},
        )
        outsider_response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/invite/",
            {"username": self.outsider.username},
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertContains(duplicate_response, "already invited")
        self.assertEqual(outsider_response.status_code, 200)
        self.assertContains(outsider_response, "Client user")
        self.assertEqual(
            ProjectInvitation.objects.filter(project=self.project).count(), 1
        )

    def test_owner_can_revoke_invitation_and_remove_member(self) -> None:
        """Owner membership controls preserve project data while removing access."""
        invitation = ProjectInvitation.objects.create(
            project=self.project, inviter=self.owner, invitee=self.invitee
        )
        revoke_response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/{invitation.pk}/revoke/"
        )

        self.assertRedirects(
            revoke_response, f"/projects/{self.project.pk}/collaborators/invite/"
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProjectInvitation.Status.REVOKED)

        membership = ProjectMembership.objects.create(
            project=self.project, user=self.invitee
        )
        remove_response = self.client.post(
            f"/projects/{self.project.pk}/collaborators/{membership.pk}/remove/"
        )

        self.assertRedirects(
            remove_response, f"/projects/{self.project.pk}/collaborators/invite/"
        )
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_owner_can_search_eligible_clients_for_invitation(self) -> None:
        """Suggestion results contain only eligible Client usernames."""
        matching_client = User.objects.create_user(username="@match-client")
        matching_client.groups.add(self.client_group)
        User.objects.create_user(username="@match-staff")
        active_client = User.objects.create_user(username="@match-active")
        active_client.groups.add(self.client_group)
        pending_client = User.objects.create_user(username="@match-pending")
        pending_client.groups.add(self.client_group)
        ProjectMembership.objects.create(project=self.project, user=active_client)
        ProjectInvitation.objects.create(
            project=self.project, inviter=self.owner, invitee=pending_client
        )

        response = self.client.get(
            f"/projects/{self.project.pk}/collaborators/suggestions/?q=@match"
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content, {"results": [{"username": "@match-client"}]}
        )

    def test_owner_invite_page_exposes_accessible_typeahead_hooks(self) -> None:
        """The invite form exposes the combobox and suggestion endpoint hooks."""
        response = self.client.get(f"/projects/{self.project.pk}/collaborators/invite/")

        self.assertContains(response, 'role="combobox"')
        self.assertContains(response, 'aria-controls="invite-suggestions"')
        self.assertContains(response, 'role="listbox"')
        self.assertContains(response, "invite_typeahead.js")

    def test_invitation_suggestions_are_owner_only(self) -> None:
        """Non-owners cannot enumerate invitation suggestions."""
        self.client.force_login(self.invitee)

        response = self.client.get(
            f"/projects/{self.project.pk}/collaborators/suggestions/?q=@"
        )

        self.assertEqual(response.status_code, 404)

    def test_invitee_workspace_shows_pending_invitation(self) -> None:
        """An invitee can discover pending invitations from the workspace."""
        invitation = ProjectInvitation.objects.create(
            project=self.project, inviter=self.owner, invitee=self.invitee
        )
        self.client.force_login(self.invitee)

        response = self.client.get("/workspace/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending invitations")
        self.assertContains(response, self.project.name)
        self.assertContains(response, self.owner.username)
        self.assertNotContains(response, str(invitation.token), html=False)

    def test_workspace_hides_terminal_invitations_and_preserves_empty_state(
        self,
    ) -> None:
        """Terminal invitations do not appear as actionable inbox entries."""
        ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.owner,
            invitee=self.invitee,
            status=ProjectInvitation.Status.DECLINED,
        )
        self.client.force_login(self.invitee)

        response = self.client.get("/workspace/")

        self.assertContains(response, "No pending invitations.")
        self.assertNotContains(response, self.project.name)

    def test_invitation_acceptance_makes_project_discoverable(self) -> None:
        """Accepting an invitation adds the project to the invitee workspace."""
        invitation = ProjectInvitation.objects.create(
            project=self.project, inviter=self.owner, invitee=self.invitee
        )
        self.client.force_login(self.invitee)
        self.client.post(f"/invitations/{invitation.token}/accept/")

        response = self.client.get("/workspace/")

        self.assertContains(response, self.project.name)


class WorkspaceTests(TestCase):
    """Verify company workspace lifecycle and authorization boundaries."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.admin = User.objects.create_user(
            username="company-admin", password="test-password"
        )
        self.admin.groups.add(self.client_group)
        self.client_user = User.objects.create_user(
            username="company-client", password="test-password"
        )
        self.client_user.groups.add(self.client_group)
        self.outsider = User.objects.create_user(
            username="company-outsider", password="test-password"
        )
        self.outsider.groups.add(self.client_group)
        self.client.force_login(self.admin)

    def test_admin_can_create_company_workspace(self) -> None:
        """Creating a company workspace assigns the creator as its admin."""
        response = self.client.post(
            "/workspaces/new/", {"name": "Acme Studio", "kind": "company"}
        )

        workspace = Workspace.objects.get(name="Acme Studio")
        self.assertRedirects(response, "/workspace/")
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                user=self.admin,
                role=WorkspaceMembership.Role.ADMIN,
                is_active=True,
            ).exists()
        )

    def test_workspace_landing_lists_active_company_workspaces(self) -> None:
        """A member can see active company workspaces from the landing page."""
        workspace = Workspace.objects.create(
            name="Visible Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.get("/workspace/")

        self.assertContains(response, "Your company workspaces")
        self.assertContains(response, workspace.name)
        self.assertContains(response, f"/workspaces/{workspace.pk}/")

    def test_workspace_creation_page_uses_shared_action_form_shell(self) -> None:
        """The workspace form matches the established authenticated form layout."""
        response = self.client.get("/workspaces/new/")

        self.assertContains(response, '<body class="auth-page action-page">')
        self.assertContains(response, "authenticated-topbar")
        self.assertContains(response, 'class="login-panel task-form-panel"')
        self.assertContains(response, 'class="eyebrow"')
        self.assertContains(response, "primary-button--full")

    def test_admin_can_invite_client_to_company_workspace(self) -> None:
        """An administrator can create a pending workspace invitation."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.post(
            f"/workspaces/{workspace.pk}/members/invite/",
            {"username": self.client_user.username},
        )

        self.assertRedirects(response, "/workspace/")
        invitation = WorkspaceInvitation.objects.get(workspace=workspace)
        self.assertEqual(invitation.invitee, self.client_user)
        self.assertTrue(invitation.is_pending)

    def test_client_can_accept_workspace_invitation(self) -> None:
        """Accepting an invitation creates an active client membership."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace, inviter=self.admin, invitee=self.client_user
        )

        self.client.force_login(self.client_user)
        response = self.client.post(f"/workspace-invitations/{invitation.pk}/accept/")

        self.assertRedirects(response, "/workspace/")
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                user=self.client_user,
                role=WorkspaceMembership.Role.CLIENT,
                is_active=True,
            ).exists()
        )

    def test_client_workspace_shows_pending_company_invitation(self) -> None:
        """A client can discover pending company invitations from the workspace."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        WorkspaceInvitation.objects.create(
            workspace=workspace, inviter=self.admin, invitee=self.client_user
        )

        self.client.force_login(self.client_user)
        response = self.client.get("/workspace/")

        self.assertContains(response, "Workspace invitations")
        self.assertContains(response, workspace.name)

    def test_client_can_decline_workspace_invitation(self) -> None:
        """Declining an invitation leaves the client outside the workspace."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace, inviter=self.admin, invitee=self.client_user
        )

        self.client.force_login(self.client_user)
        response = self.client.post(f"/workspace-invitations/{invitation.pk}/decline/")

        self.assertRedirects(response, "/workspace/")
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, WorkspaceInvitation.Status.DECLINED)
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=workspace, user=self.client_user, is_active=True
            ).exists()
        )

    def test_admin_can_revoke_workspace_invitation(self) -> None:
        """An administrator can revoke a pending workspace invitation."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace, inviter=self.admin, invitee=self.client_user
        )

        response = self.client.post(
            f"/workspaces/{workspace.pk}/members/invitations/{invitation.pk}/revoke/"
        )

        self.assertRedirects(response, "/workspace/")
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, WorkspaceInvitation.Status.REVOKED)

    def test_client_cannot_manage_company_members(self) -> None:
        """Company clients cannot access administrator member controls."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.client_user,
            role=WorkspaceMembership.Role.CLIENT,
        )

        self.client.force_login(self.client_user)
        response = self.client.get(f"/workspaces/{workspace.pk}/members/")

        self.assertEqual(response.status_code, 403)

    def test_admin_member_page_exposes_invitation_form(self) -> None:
        """Administrators can see the client invitation input on the member page."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.get(f"/workspaces/{workspace.pk}/members/")

        self.assertContains(response, 'name="username"')
        self.assertContains(response, "Invite client")

    def test_admin_member_page_exposes_remove_and_revoke_controls(self) -> None:
        """Administrators can see controls for members and pending invitations."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        member = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.client_user,
            role=WorkspaceMembership.Role.CLIENT,
        )
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace, inviter=self.admin, invitee=self.outsider
        )

        response = self.client.get(f"/workspaces/{workspace.pk}/members/")

        self.assertContains(
            response,
            f"/workspaces/{workspace.pk}/members/{member.pk}/remove/",
        )
        self.assertContains(
            response,
            f"/workspaces/{workspace.pk}/members/invitations/{invitation.pk}/revoke/",
        )
        self.assertContains(response, "Are you sure")

    def test_last_admin_cannot_be_removed(self) -> None:
        """The final active company administrator cannot be removed."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        membership = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.post(
            f"/workspaces/{workspace.pk}/members/{membership.pk}/remove/"
        )

        self.assertEqual(response.status_code, 400)
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

    def test_admin_can_promote_member_to_admin(self) -> None:
        """An administrator can promote an active client member."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        membership = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.client_user,
            role=WorkspaceMembership.Role.CLIENT,
        )

        response = self.client.post(
            f"/workspaces/{workspace.pk}/members/{membership.pk}/role/",
            {"role": WorkspaceMembership.Role.ADMIN},
        )

        self.assertRedirects(response, f"/workspaces/{workspace.pk}/members/")
        membership.refresh_from_db()
        self.assertEqual(membership.role, WorkspaceMembership.Role.ADMIN)

    def test_last_admin_cannot_be_demoted(self) -> None:
        """The final active administrator cannot be demoted to client."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        membership = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        response = self.client.post(
            f"/workspaces/{workspace.pk}/members/{membership.pk}/role/",
            {"role": WorkspaceMembership.Role.CLIENT},
        )

        self.assertEqual(response.status_code, 400)
        membership.refresh_from_db()
        self.assertEqual(membership.role, WorkspaceMembership.Role.ADMIN)

    def test_membership_service_protects_last_admin(self) -> None:
        """The membership service protects the invariant outside HTTP views."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        membership = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )

        with self.assertRaises(LastAdministratorError):
            change_membership_role(membership, WorkspaceMembership.Role.CLIENT)
        with self.assertRaises(LastAdministratorError):
            deactivate_membership(membership)

        membership.refresh_from_db()
        self.assertEqual(membership.role, WorkspaceMembership.Role.ADMIN)
        self.assertTrue(membership.is_active)

    def test_outsider_cannot_view_company_workspace_members(self) -> None:
        """Users outside a company workspace cannot inspect its members."""
        workspace = Workspace.objects.create(
            name="Acme Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        self.client.force_login(self.outsider)

        response = self.client.get(f"/workspaces/{workspace.pk}/members/")

        self.assertEqual(response.status_code, 403)


class WorkspaceProjectAuthorizationTests(TestCase):
    """Verify project access through active company workspace membership."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.admin = User.objects.create_user(
            username="workspace-project-admin", password="test-password"
        )
        self.admin.groups.add(self.client_group)
        self.member = User.objects.create_user(
            username="workspace-project-member", password="test-password"
        )
        self.member.groups.add(self.client_group)
        self.outsider = User.objects.create_user(
            username="workspace-project-outsider", password="test-password"
        )
        self.outsider.groups.add(self.client_group)
        self.workspace = Workspace.objects.create(
            name="Client Delivery", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=WorkspaceMembership.Role.CLIENT,
        )

    def test_company_admin_can_create_project_in_company_workspace(self) -> None:
        """An administrator can create a project assigned to the company workspace."""
        self.client.force_login(self.admin)

        response = self.client.post(
            "/projects/new/",
            {
                "name": "Client launch",
                "description": "Shared delivery work",
                "workspace": self.workspace.pk,
            },
        )

        project = Project.objects.get(name="Client launch")
        self.assertRedirects(response, project.get_absolute_url())
        self.assertEqual(project.workspace, self.workspace)

    def test_company_member_can_view_workspace_project_without_project_membership(
        self,
    ) -> None:
        """Workspace membership grants project visibility without project membership."""
        project = Project.objects.create(
            client=self.admin, workspace=self.workspace, name="Shared delivery"
        )
        self.client.force_login(self.member)

        self.assertEqual(self.client.get(project.get_absolute_url()).status_code, 200)
        self.assertContains(self.client.get("/projects/"), project.name)

    def test_non_member_cannot_view_company_workspace_project(self) -> None:
        """A user outside the company workspace cannot access its project."""
        project = Project.objects.create(
            client=self.admin, workspace=self.workspace, name="Private delivery"
        )
        self.client.force_login(self.outsider)

        self.assertEqual(self.client.get(project.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get("/projects/").status_code, 200)
        self.assertNotContains(self.client.get("/projects/"), project.name)


class WorkspaceManagementContextTests(TestCase):
    """Verify company management stays inside the selected workspace context."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.admin = User.objects.create_user(
            username="context-admin", password="test-password"
        )
        self.admin.groups.add(self.client_group)
        self.member = User.objects.create_user(
            username="context-member", password="test-password"
        )
        self.member.groups.add(self.client_group)
        self.outsider = User.objects.create_user(
            username="context-outsider", password="test-password"
        )
        self.outsider.groups.add(self.client_group)
        self.workspace = Workspace.objects.create(
            name="Selected Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.admin,
            role=WorkspaceMembership.Role.ADMIN,
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=WorkspaceMembership.Role.CLIENT,
        )
        self.project = Project.objects.create(
            client=self.admin,
            workspace=self.workspace,
            name="Company project",
        )
        self.task = Task.objects.create(
            client=self.admin,
            project=self.project,
            title="Company task",
        )

    def test_workspace_home_shows_selected_context_and_navigation(self) -> None:
        """A member enters a company shell that identifies the selected workspace."""
        self.client.force_login(self.member)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.workspace.name)
        self.assertContains(response, "Company project")
        self.assertContains(response, "Client overview")
        self.assertContains(response, f"/workspaces/{self.workspace.pk}/projects/")
        self.assertContains(response, f"/workspaces/{self.workspace.pk}/tasks/")

    def test_company_project_and_task_pages_are_workspace_scoped(self) -> None:
        """Company project and task lists stay inside the selected workspace."""
        self.client.force_login(self.member)

        project_response = self.client.get(f"/workspaces/{self.workspace.pk}/projects/")
        task_response = self.client.get(f"/workspaces/{self.workspace.pk}/tasks/")

        self.assertContains(project_response, self.project.name)
        self.assertContains(task_response, self.task.title)
        self.assertContains(
            project_response, f"/workspaces/{self.workspace.pk}/projects/new/"
        )
        self.assertContains(
            task_response, f"/workspaces/{self.workspace.pk}/tasks/new/"
        )
        self.assertContains(task_response, 'data-task-view="lanes"')
        self.assertContains(task_response, 'data-task-view="list"')
        self.assertContains(
            task_response,
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/status/",
        )

        project_detail_response = self.client.get(
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/"
        )
        self.assertContains(project_detail_response, "Project tasks")
        self.assertContains(project_detail_response, 'data-task-view="lanes"')

    def test_company_project_creation_preserves_selected_workspace(self) -> None:
        """A company admin creates projects through the selected workspace route."""
        self.client.force_login(self.admin)

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/projects/new/",
            {"name": "Context project", "description": "Scoped work"},
        )

        project = Project.objects.get(name="Context project")
        self.assertRedirects(response, f"/workspaces/{self.workspace.pk}/projects/")
        self.assertEqual(project.workspace, self.workspace)

    def test_company_member_cannot_create_project_in_workspace_context(self) -> None:
        """Workspace clients cannot create projects through admin routes."""
        self.client.force_login(self.member)

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/projects/new/",
            {"name": "Unauthorized project", "description": "No access"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Project.objects.filter(name="Unauthorized project").exists())

    def test_workspace_project_form_locks_selected_workspace(self) -> None:
        """Workspace project creation displays its route workspace as fixed."""
        self.client.force_login(self.admin)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/projects/new/")

        form = response.context["form"]
        self.assertEqual(form.fields["workspace"].initial, self.workspace.pk)
        self.assertTrue(form.fields["workspace"].disabled)
        self.assertContains(response, self.workspace.name)
        self.assertContains(response, "disabled")

    def test_workspace_project_invalid_submission_preserves_context_and_values(
        self,
    ) -> None:
        """Invalid workspace project submissions retain context and values."""
        self.client.force_login(self.admin)

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/projects/new/",
            {
                "name": self.project.name,
                "description": "Keep this project description",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.workspace.name)
        self.assertContains(response, "Keep this project description")
        self.assertContains(response, "You already have a project with this name.")
        self.assertEqual(
            response.context["form"]["workspace"].value(), self.workspace.pk
        )
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'aria-describedby="id_name-error"')
        self.assertContains(response, 'id="id_name-error"')

    def test_workspace_project_list_links_to_project_detail(self) -> None:
        """Workspace project cards open the selected project context."""
        self.client.force_login(self.member)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/projects/")

        self.assertContains(
            response,
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/",
        )

    def test_admin_can_edit_project_in_workspace_context(self) -> None:
        """Workspace administrators can edit projects without losing context."""
        self.client.force_login(self.admin)
        self.project.client = self.member
        self.project.save(update_fields=["client"])

        response = self.client.get(
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/edit/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit project")
        self.assertContains(response, "Save changes")
        self.assertContains(response, self.workspace.name)
        self.assertContains(response, "disabled")

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/edit/",
            {
                "name": "Updated company project",
                "description": "Updated context",
            },
        )

        self.assertRedirects(
            response,
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/",
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.workspace, self.workspace)
        self.assertEqual(self.project.client, self.member)
        self.assertEqual(self.project.name, "Updated company project")

    def test_company_member_cannot_edit_project_in_workspace_context(self) -> None:
        """Workspace clients cannot use the administrator project edit route."""
        self.client.force_login(self.member)

        response = self.client.get(
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/edit/"
        )

        self.assertEqual(response.status_code, 403)

    def test_workspace_create_forms_render_selected_context(self) -> None:
        """Workspace project and task forms render without losing route context."""
        self.client.force_login(self.admin)

        project_response = self.client.get(
            f"/workspaces/{self.workspace.pk}/projects/new/"
        )
        task_response = self.client.get(f"/workspaces/{self.workspace.pk}/tasks/new/")

        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(task_response.status_code, 200)
        self.assertContains(project_response, self.workspace.name)
        self.assertContains(task_response, self.workspace.name)

    def test_workspace_project_context_prefills_task_create(self) -> None:
        """Workspace project pages lock task creation to their project."""
        self.client.force_login(self.member)

        response = self.client.get(
            f"/workspaces/{self.workspace.pk}/tasks/new/?project={self.project.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project_context"], self.project)
        self.assertContains(response, self.project.name)
        self.assertContains(response, 'name="project"')
        self.assertContains(response, "disabled")

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/tasks/new/?project={self.project.pk}",
            {
                "title": "Contextual company task",
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
            },
        )

        self.assertRedirects(response, f"/workspaces/{self.workspace.pk}/tasks/")
        self.assertTrue(
            Task.objects.filter(
                title="Contextual company task", project=self.project
            ).exists()
        )

    def test_workspace_project_context_preserves_invalid_task_submission(self) -> None:
        """Invalid contextual task submissions retain the project and values."""
        self.client.force_login(self.member)

        response = self.client.post(
            f"/workspaces/{self.workspace.pk}/tasks/new/?project={self.project.pk}",
            {
                "title": "",
                "description": "Keep this description",
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.HIGH,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project_context"], self.project)
        self.assertContains(response, self.project.name)
        self.assertContains(response, "Keep this description")
        self.assertContains(response, "This field is required")

    def test_workspace_task_edit_form_uses_edit_actions(self) -> None:
        """Workspace task edits preserve values and identify the edit action."""
        self.client.force_login(self.member)

        response = self.client.get(
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/edit/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit task")
        self.assertContains(response, "Save changes")
        self.assertContains(response, self.task.title)
        self.assertContains(response, self.project.name)

    def test_workspace_project_detail_links_task_creation_to_project(self) -> None:
        """Workspace project details pass their project into task creation."""
        self.client.force_login(self.member)

        response = self.client.get(
            f"/workspaces/{self.workspace.pk}/projects/{self.project.pk}/"
        )

        self.assertContains(
            response,
            f"/workspaces/{self.workspace.pk}/tasks/new/?project={self.project.pk}",
        )

    def test_client_overview_does_not_show_company_project(self) -> None:
        """The personal overview does not become a company management dashboard."""
        self.client.force_login(self.member)

        response = self.client.get("/workspace/")

        self.assertNotContains(response, self.project.name)
        self.assertNotContains(response, self.task.title)
        self.assertContains(response, self.workspace.name)

    def test_non_member_cannot_enter_selected_workspace(self) -> None:
        """A non-member cannot access or enumerate the selected workspace."""
        self.client.force_login(self.outsider)

        for path in (
            f"/workspaces/{self.workspace.pk}/",
            f"/workspaces/{self.workspace.pk}/projects/",
            f"/workspaces/{self.workspace.pk}/tasks/",
        ):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (403, 404))

    def test_workspace_switcher_lists_active_memberships(self) -> None:
        """The selected workspace shell exposes other active workspaces."""
        second_workspace = Workspace.objects.create(
            name="Second Studio", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=second_workspace,
            user=self.member,
            role=WorkspaceMembership.Role.CLIENT,
        )
        self.client.force_login(self.member)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/")

        self.assertContains(response, second_workspace.name)
        self.assertContains(response, f"/workspaces/{second_workspace.pk}/")

    def test_company_task_detail_and_mutations_stay_in_workspace(self) -> None:
        """Company task detail and mutations preserve the selected workspace."""
        self.client.force_login(self.member)

        detail_response = self.client.get(
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/"
        )
        update_response = self.client.post(
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/edit/",
            {
                "project": self.project.pk,
                "title": "Updated company task",
                "status": Task.Status.IN_PROGRESS,
                "priority": Task.Priority.HIGH,
                "due_date": "",
            },
        )
        status_response = self.client.post(
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/status/",
            {"status": Task.Status.COMPLETED},
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertRedirects(
            update_response,
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/",
        )
        self.assertEqual(status_response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_non_member_cannot_use_workspace_task_routes(self) -> None:
        """A non-member cannot read or mutate a company task through scoped routes."""
        self.client.force_login(self.outsider)

        for path in (
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/",
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/edit/",
            f"/workspaces/{self.workspace.pk}/tasks/{self.task.pk}/delete/",
        ):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (403, 404))

    def test_admin_can_manage_workspace_settings(self) -> None:
        """Only an administrator can view and update selected workspace settings."""
        self.client.force_login(self.admin)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/settings/")
        update_response = self.client.post(
            f"/workspaces/{self.workspace.pk}/settings/",
            {"name": "Renamed Studio"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(update_response, f"/workspaces/{self.workspace.pk}/")
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.name, "Renamed Studio")

    def test_client_cannot_manage_workspace_settings(self) -> None:
        """Company clients cannot access administrator-only settings."""
        self.client.force_login(self.member)

        response = self.client.get(f"/workspaces/{self.workspace.pk}/settings/")

        self.assertEqual(response.status_code, 403)


class TaskAssignmentTests(TestCase):
    """Verify task assignment eligibility, validation, persistence, and UI rendering."""

    def setUp(self) -> None:
        self.client_group = Group.objects.create(name="Client")
        self.owner = User.objects.create_user(
            username="project-owner", password="test-password"
        )
        self.owner.groups.add(self.client_group)
        self.project_member = User.objects.create_user(
            username="project-member", password="test-password"
        )
        self.project_member.groups.add(self.client_group)
        self.workspace_member = User.objects.create_user(
            username="workspace-member", password="test-password"
        )
        self.workspace_member.groups.add(self.client_group)
        self.pending_invitee = User.objects.create_user(
            username="pending-invitee", password="test-password"
        )
        self.pending_invitee.groups.add(self.client_group)
        self.outsider = User.objects.create_user(
            username="outsider-user", password="test-password"
        )
        self.outsider.groups.add(self.client_group)

        self.workspace = Workspace.objects.create(
            name="Collaborative Workspace", kind=Workspace.Kind.COMPANY
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.owner,
            role=WorkspaceMembership.Role.ADMIN,
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.workspace_member,
            role=WorkspaceMembership.Role.CLIENT,
        )
        WorkspaceInvitation.objects.create(
            workspace=self.workspace,
            inviter=self.owner,
            invitee=self.pending_invitee,
            status=WorkspaceInvitation.Status.PENDING,
        )

        self.project = Project.objects.create(
            client=self.owner,
            workspace=self.workspace,
            name="Assignment Project",
        )
        ProjectMembership.objects.create(
            project=self.project,
            user=self.project_member,
            is_active=True,
        )
        ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.owner,
            invitee=self.pending_invitee,
            status=ProjectInvitation.Status.PENDING,
        )

    def test_eligible_task_assignees_includes_members(self) -> None:
        """Eligible assignees include project owner and active members."""
        from core.services import get_eligible_task_assignees

        eligible_assignees = get_eligible_task_assignees(self.project)

        self.assertIn(self.owner, eligible_assignees)
        self.assertIn(self.project_member, eligible_assignees)
        self.assertIn(self.workspace_member, eligible_assignees)
        self.assertNotIn(self.pending_invitee, eligible_assignees)
        self.assertNotIn(self.outsider, eligible_assignees)

    def test_create_task_with_valid_assignment(self) -> None:
        """A task can be assigned to an eligible member upon creation."""
        self.client.force_login(self.owner)

        response = self.client.post(
            "/tasks/new/",
            {
                "project": self.project.pk,
                "title": "Assigned Task",
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
                "assigned_to": self.project_member.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(title="Assigned Task")
        self.assertEqual(task.assigned_to, self.project_member)

    def test_create_task_rejects_ineligible_assignment(self) -> None:
        """Assigning a task to a non-member raises a form validation error."""
        self.client.force_login(self.owner)

        response = self.client.post(
            "/tasks/new/",
            {
                "project": self.project.pk,
                "title": "Invalid Assigned Task",
                "status": Task.Status.OUTSTANDING,
                "priority": Task.Priority.MEDIUM,
                "assigned_to": self.outsider.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            "form",
            "assigned_to",
            "Select a valid choice. That choice is not one of the available choices.",
        )
        self.assertFalse(Task.objects.filter(title="Invalid Assigned Task").exists())

    def test_task_detail_and_list_views_render_assignee_badge(self) -> None:
        """Task detail, list, and board views display assigned username badge."""
        task = Task.objects.create(
            client=self.owner,
            project=self.project,
            title="Detailed Task",
            assigned_to=self.project_member,
        )
        unassigned_task = Task.objects.create(
            client=self.owner,
            project=self.project,
            title="Unassigned Task",
            assigned_to=None,
        )

        self.client.force_login(self.owner)

        detail_response = self.client.get(f"/tasks/{task.pk}/")
        self.assertContains(detail_response, "Assigned client")
        self.assertContains(detail_response, self.project_member.username)

        unassigned_detail_response = self.client.get(f"/tasks/{unassigned_task.pk}/")
        self.assertContains(unassigned_detail_response, "Assigned client")
        self.assertContains(unassigned_detail_response, "Unassigned")

        list_response = self.client.get(f"/projects/{self.project.pk}/")
        self.assertContains(list_response, self.project_member.username)
        self.assertContains(list_response, "Unassigned")

    def test_task_detail_pages_use_full_width_layout(self) -> None:
        """Personal and workspace detail pages use full-width task-page class."""
        task = Task.objects.create(
            client=self.owner,
            project=self.project,
            title="Layout Test Task",
        )
        self.client.force_login(self.owner)

        personal_response = self.client.get(f"/tasks/{task.pk}/")
        workspace_response = self.client.get(
            f"/workspaces/{self.workspace.pk}/tasks/{task.pk}/"
        )

        self.assertContains(personal_response, 'class="detail-panel task-page"')
        self.assertContains(workspace_response, 'class="detail-panel task-page"')
