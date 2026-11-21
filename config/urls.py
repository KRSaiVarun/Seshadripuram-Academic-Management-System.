from django.contrib import admin
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from accounts import views as account_views
from accounts import api as account_api

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "application": "Seshadripuram College Academic Management System", "phase": 2})

urlpatterns = [
    path("", account_views.dashboard, name="dashboard"),
    path(
        "hod/dashboard/",
        account_views.role_dashboard,
        {"role": "HOD"},
        name="hod-dashboard",
    ),
    path(
        "faculty/dashboard/",
        account_views.role_dashboard,
        {"role": "FACULTY"},
        name="faculty-dashboard",
    ),
    path(
        "student/dashboard/",
        account_views.role_dashboard,
        {"role": "STUDENT"},
        name="student-dashboard",
    ),
    path("students/", account_views.manage_students, name="managed-students"),
    path("students/add/", account_views.add_managed_student, name="managed-student-add"),
    path(
        "students/<int:pk>/edit/",
        account_views.edit_managed_student,
        name="managed-student-edit",
    ),
    path("password/change/", account_views.change_password, name="password-change"),
    path("faculty/", account_views.faculty_directory, name="faculty-directory"),
    path(
        "faculty/<int:pk>/",
        account_views.faculty_profile_detail,
        name="faculty-profile",
    ),
    path("subjects/<int:pk>/edit/", account_views.edit_subject, name="subject-edit"),
    path("login/", account_views.sign_in, name="login"),
    path("logout/", account_views.sign_out, name="logout"),
    path("admin/", admin.site.urls),
    path("api/health/", health, name="api-health"),
    path("api/desktop/login/", account_api.desktop_login, name="desktop-login"),
    path("api/desktop/summary/", account_api.desktop_summary, name="desktop-summary"),
]
