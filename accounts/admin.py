from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters

from academics.permissions import is_academic_admin
from academics.audit import AuditedModelAdmin, record_sensitive_update
from academics.models import Faculty, Student
from .models import User

PRIVILEGED_ROLES = {
    User.Role.SUPER_ADMIN,
    User.Role.ADMIN,
    User.Role.PRINCIPAL,
    User.Role.HOD,
    User.Role.EXAM,
}


@admin.register(User)
class CustomUserAdmin(AuditedModelAdmin, UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("College access", {"fields": ("role", "phone")}),
        ("Institutional profile", {
            "fields": ("designation", "qualifications", "institution", "profile_photo_url")
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("College access", {"fields": ("role", "phone")}),
        ("Institutional profile", {
            "fields": ("designation", "qualifications", "institution", "profile_photo_url")
        }),
    )
    list_display = (
        "username", "email", "first_name", "last_name", "designation", "role", "is_active"
    )
    list_filter = ("role", "is_active")

    @staticmethod
    def _is_hod(user):
        return user.is_authenticated and user.role == User.Role.HOD and not user.is_superuser

    def has_module_permission(self, request):
        return is_academic_admin(request.user) or (
            self._is_hod(request.user)
            and request.user.headed_departments.exists()
        )

    @staticmethod
    def _hod_can_access_user(request, obj):
        if obj.role == User.Role.STUDENT:
            return Student.objects.filter(
                user=obj, department__hod_id=request.user.pk
            ).exists()
        if obj.role == User.Role.FACULTY:
            return Faculty.objects.filter(
                user=obj, department__hod_id=request.user.pk
            ).exists()
        return False

    def has_view_permission(self, request, obj=None):
        if not is_academic_admin(request.user) and not self._is_hod(request.user):
            return False
        if (
            obj is not None
            and not request.user.is_superuser
            and (
                obj.is_superuser
                or obj.role in PRIVILEGED_ROLES
            )
        ):
            return False
        if self._is_hod(request.user) and obj is not None:
            return not obj.is_superuser and obj.role in {
                User.Role.FACULTY, User.Role.STUDENT
            } and self._hod_can_access_user(request, obj)
        return True

    def has_add_permission(self, request):
        return is_academic_admin(request.user) or (
            self._is_hod(request.user)
            and request.user.headed_departments.exists()
        )

    def has_change_permission(self, request, obj=None):
        if not is_academic_admin(request.user) and not self._is_hod(request.user):
            return False
        if (
            obj is not None
            and not request.user.is_superuser
            and (
                obj.is_superuser
                or obj.role in PRIVILEGED_ROLES
            )
        ):
            return False
        if self._is_hod(request.user) and obj is not None:
            return not obj.is_superuser and obj.role in {
                User.Role.FACULTY, User.Role.STUDENT
            } and self._hod_can_access_user(request, obj)
        return True

    def has_delete_permission(self, request, obj=None):
        if self._is_hod(request.user):
            return False
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.exclude(
                is_superuser=True,
            ).exclude(role__in=PRIVILEGED_ROLES)
        if self._is_hod(request.user):
            return queryset.filter(
                is_superuser=False,
                role__in=(User.Role.FACULTY, User.Role.STUDENT),
            ).filter(
                Q(faculty_profile__department__hod=request.user)
                | Q(student_profile__department__hod=request.user)
            ).distinct()
        return queryset

    def get_fieldsets(self, request, obj=None):
        if not request.user.is_superuser:
            if obj is None:
                return self.get_add_fieldsets(request, obj)
            return (
                (None, {"fields": ("username", "first_name", "last_name", "email")}),
                ("College access", {"fields": ("role", "phone", "is_active")}),
                ("Institutional profile", {
                    "fields": ("designation", "qualifications", "institution", "profile_photo_url")
                }),
            )
        return super().get_fieldsets(request, obj)

    def get_add_fieldsets(self, request, obj=None):
        if not request.user.is_superuser:
            return (
                (None, {
                    "classes": ("wide",),
                    "fields": (
                        "username", "first_name", "last_name", "email", "phone",
                        "role", "password1", "password2",
                    ),
                }),
            )
        return super().get_add_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "role" in form.base_fields and not request.user.is_superuser:
            if obj is not None:
                role_choices = ((obj.role, obj.get_role_display()),)
            else:
                role_choices = (
                    (User.Role.FACULTY, User.Role.FACULTY.label),
                    (User.Role.STUDENT, User.Role.STUDENT.label),
                )
            form.base_fields["role"].choices = role_choices
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self._is_hod(request.user) and db_field.name == "user_permissions":
            kwargs["queryset"] = kwargs.get("queryset", db_field.remote_field.model.objects).none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if obj.role == User.Role.SUPER_ADMIN:
                raise PermissionDenied
            obj.is_staff = obj.role == User.Role.FACULTY
            obj.is_superuser = False
            if not change:
                obj.must_change_password = True
        elif obj.role == User.Role.SUPER_ADMIN:
            obj.is_staff = True
            obj.is_superuser = True
        super().save_model(request, obj, form, change)

    @method_decorator(sensitive_post_parameters())
    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, unquote(id))
        if user is None:
            raise Http404
        previous_password = user.password
        response = super().user_change_password(request, id, form_url)
        if request.method == "POST" and response.status_code == 302:
            user.refresh_from_db()
            if user.password != previous_password:
                user.must_change_password = True
                user.save(update_fields=("must_change_password",))
                record_sensitive_update(
                    request,
                    user,
                    "password",
                    "Password reset through Django admin.",
                )
        return response
