"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from core.views import (
    ClientLandingPageView,
    ClientRegistrationView,
    ClientProjectCreateView,
    ClientProjectDeleteView,
    ClientProjectDetailView,
    ClientProjectListView,
    ClientProjectInviteView,
    ClientProjectInviteSuggestionsView,
    ClientProjectInvitationRevokeView,
    ClientProjectInvitationDeclineView,
    ClientProjectMemberRemoveView,
    ClientProjectUpdateView,
    ClientProfileView,
    ClientPasswordChangeView,
    ClientTaskCreateView,
    ClientTaskDeleteView,
    ClientTaskDetailView,
    ClientTaskStatusView,
    ClientTaskUpdateView,
    ClientProjectInvitationAcceptView,
    ClientProjectInvitationReviewView,
    ClientProjectInvitationAcceptByIdView,
    ClientProjectInvitationDeclineByIdView,
    HealthCheckView,
    PublicLandingPageView,
    WorkspaceCreateView,
    WorkspaceInviteView,
    WorkspaceInvitationAcceptView,
    WorkspaceInvitationDeclineView,
    WorkspaceInvitationRevokeView,
    WorkspaceMemberListView,
    WorkspaceMemberRemoveView,
    WorkspaceMemberRoleView,
)

urlpatterns = [
    path("", PublicLandingPageView.as_view(), name="public-landing"),
    path("workspace/", ClientLandingPageView.as_view(), name="client-landing"),
    path("workspaces/new/", WorkspaceCreateView.as_view(), name="workspace-create"),
    path(
        "workspaces/<int:pk>/members/",
        WorkspaceMemberListView.as_view(),
        name="workspace-members",
    ),
    path(
        "workspaces/<int:pk>/members/invite/",
        WorkspaceInviteView.as_view(),
        name="workspace-invite",
    ),
    path(
        "workspaces/<int:pk>/members/<int:membership_id>/remove/",
        WorkspaceMemberRemoveView.as_view(),
        name="workspace-member-remove",
    ),
    path(
        "workspaces/<int:pk>/members/<int:membership_id>/role/",
        WorkspaceMemberRoleView.as_view(),
        name="workspace-member-role",
    ),
    path(
        "workspace-invitations/<int:pk>/accept/",
        WorkspaceInvitationAcceptView.as_view(),
        name="workspace-invitation-accept",
    ),
    path(
        "workspace-invitations/<int:pk>/decline/",
        WorkspaceInvitationDeclineView.as_view(),
        name="workspace-invitation-decline",
    ),
    path(
        "workspaces/<int:pk>/members/invitations/<int:invitation_id>/revoke/",
        WorkspaceInvitationRevokeView.as_view(),
        name="workspace-invitation-revoke",
    ),
    path("accounts/register/", ClientRegistrationView.as_view(), name="register"),
    path("profile/", ClientProfileView.as_view(), name="profile"),
    path(
        "profile/password/",
        ClientPasswordChangeView.as_view(),
        name="password-change",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("projects/", ClientProjectListView.as_view(), name="project-list"),
    path("projects/new/", ClientProjectCreateView.as_view(), name="project-create"),
    path(
        "projects/<int:pk>/", ClientProjectDetailView.as_view(), name="project-detail"
    ),
    path(
        "projects/<int:pk>/edit/",
        ClientProjectUpdateView.as_view(),
        name="project-update",
    ),
    path(
        "projects/<int:pk>/delete/",
        ClientProjectDeleteView.as_view(),
        name="project-delete",
    ),
    path(
        "projects/<int:pk>/collaborators/invite/",
        ClientProjectInviteView.as_view(),
        name="project-invite",
    ),
    path(
        "projects/<int:pk>/collaborators/suggestions/",
        ClientProjectInviteSuggestionsView.as_view(),
        name="project-invite-suggestions",
    ),
    path(
        "invitations/<uuid:token>/accept/",
        ClientProjectInvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path(
        "invitations/<int:pk>/",
        ClientProjectInvitationReviewView.as_view(),
        name="invitation-review",
    ),
    path(
        "invitations/<int:pk>/accept/",
        ClientProjectInvitationAcceptByIdView.as_view(),
        name="invitation-accept-by-id",
    ),
    path(
        "invitations/<int:pk>/decline/",
        ClientProjectInvitationDeclineByIdView.as_view(),
        name="invitation-decline-by-id",
    ),
    path(
        "invitations/<uuid:token>/decline/",
        ClientProjectInvitationDeclineView.as_view(),
        name="invitation-decline",
    ),
    path(
        "projects/<int:pk>/collaborators/<int:invitation_id>/revoke/",
        ClientProjectInvitationRevokeView.as_view(),
        name="project-invitation-revoke",
    ),
    path(
        "projects/<int:pk>/collaborators/<int:membership_id>/remove/",
        ClientProjectMemberRemoveView.as_view(),
        name="project-member-remove",
    ),
    path("tasks/new/", ClientTaskCreateView.as_view(), name="task-create"),
    path("tasks/<int:pk>/", ClientTaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/edit/", ClientTaskUpdateView.as_view(), name="task-update"),
    path(
        "tasks/<int:pk>/status/",
        ClientTaskStatusView.as_view(),
        name="task-status",
    ),
    path(
        "tasks/<int:pk>/delete/",
        ClientTaskDeleteView.as_view(),
        name="task-delete",
    ),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("admin/", admin.site.urls),
]
