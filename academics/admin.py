import csv

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify

from .audit import (
    AuditLogAdmin,
    AuditedModelAdmin,
    capture_snapshot,
    record_update,
)
from .models import (
    AcademicYear,
    AuditLog,
    Department,
    FacultyDirectoryProfile,
    Faculty,
    Program,
    Semester,
    Student,
    Subject,
)
from .permissions import can_manage_department, is_academic_admin


class AcademicAdmin(AuditedModelAdmin):
    def _is_hod(self, user):
        return user.is_authenticated and user.role == "HOD"

    def has_module_permission(self, request):
        if is_academic_admin(request.user):
            return True
        if not self._is_hod(request.user):
            return False
        return self.model in {Student, Faculty, Subject, Program, Semester}

    @staticmethod
    def _department_for_object(obj):
        if isinstance(obj, Department):
            return obj
        if isinstance(obj, (Student, Faculty)):
            return obj.department
        if isinstance(obj, Program):
            return obj.department
        if isinstance(obj, Semester):
            return obj.program.department
        if isinstance(obj, Subject):
            return obj.semester.program.department
        if isinstance(obj, AcademicYear):
            student = obj.student_set.select_related("department").first()
            return student.department if student else None
        return None

    def _object_is_in_hod_scope(self, request, obj):
        if not self._is_hod(request.user):
            return True
        if isinstance(obj, AcademicYear):
            return Student.objects.filter(
                academic_year=obj,
                department__hod=request.user,
            ).exists()
        department = self._department_for_object(obj)
        return department is not None and can_manage_department(request.user, department)

    def has_view_permission(self, request, obj=None):
        return is_academic_admin(request.user) or (
            self.has_module_permission(request)
            and (obj is None or self._object_is_in_hod_scope(request, obj))
        )

    def has_add_permission(self, request):
        if is_academic_admin(request.user):
            return True
        return self._is_hod(request.user) and self.model in {
            Student, Faculty, Subject
        }

    def has_change_permission(self, request, obj=None):
        return is_academic_admin(request.user) or (
            self.has_module_permission(request)
            and (obj is None or self._object_is_in_hod_scope(request, obj))
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj) and (
            obj is None or not self._has_related_academic_records(obj)
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not self._is_hod(request.user):
            return queryset
        department_scope = {"hod": request.user}
        if self.model is Department:
            return queryset.filter(**department_scope)
        if self.model in {Student, Faculty}:
            return queryset.filter(department__hod=request.user)
        if self.model is Program:
            return queryset.filter(department__hod=request.user)
        if self.model is Semester:
            return queryset.filter(program__department__hod=request.user)
        if self.model is Subject:
            return queryset.filter(semester__program__department__hod=request.user)
        if self.model is AcademicYear:
            return queryset.filter(
                pk__in=Student.objects.filter(department__hod=request.user)
                .values("academic_year_id")
            )
        return queryset.none()

    def save_model(self, request, obj, form, change):
        if self._is_hod(request.user):
            department = self._department_for_object(obj)
            if department is None or not can_manage_department(request.user, department):
                raise PermissionDenied
        super().save_model(request, obj, form, change)

    @staticmethod
    def _has_related_academic_records(obj):
        if isinstance(obj, Department):
            return (
                Program.objects.filter(department=obj).exists()
                or Student.objects.filter(department=obj).exists()
                or Faculty.objects.filter(department=obj).exists()
            )
        if isinstance(obj, Program):
            return (
                Semester.objects.filter(program=obj).exists()
                or Student.objects.filter(program=obj).exists()
            )
        if isinstance(obj, Semester):
            return (
                Student.objects.filter(semester=obj).exists()
                or Subject.objects.filter(semester=obj).exists()
            )
        if isinstance(obj, AcademicYear):
            return Student.objects.filter(academic_year=obj).exists()
        return False

    def delete_queryset(self, request, queryset):
        related_records = [
            obj for obj in queryset if self._has_related_academic_records(obj)
        ]
        if related_records:
            raise ProtectedError(
                "Archive this record or reassign its academic records before deleting it.",
                related_records,
            )
        super().delete_queryset(request, queryset)


@admin.register(Department)
class DepartmentAdmin(AcademicAdmin):
    list_display = (
        "code", "name", "department_type", "hod", "is_active",
    )
    list_filter = ("department_type", "is_active")
    search_fields = ("code", "name", "official_reference")

@admin.register(Program)
class ProgramAdmin(AcademicAdmin):
    list_display = ("code", "name", "department", "duration_years", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("code", "name")


@admin.register(AcademicYear)
class AcademicYearAdmin(AcademicAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    search_fields = ("name",)
    list_filter = ("is_current",)


@admin.register(Semester)
class SemesterAdmin(AcademicAdmin):
    list_display = ("program", "number", "name")
    list_filter = ("program",)
    search_fields = ("program__code", "program__name", "name")


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = "__all__"
        widgets = {"date_of_birth": AdminDateWidget}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        date_field = self.fields.get("date_of_birth")
        if date_field and "%d-%m-%Y" not in date_field.input_formats:
            date_field.input_formats = [*date_field.input_formats, "%d-%m-%Y"]


@admin.register(Student)
class StudentAdmin(AcademicAdmin):
    form = StudentAdminForm
    list_display = (
        "source_serial_number", "user", "admission_number", "program",
        "semester", "department", "status", "registration_review_required",
    )
    list_display_links = ("user", "admission_number")
    list_filter = ("department", "program", "semester", "status")
    search_fields = ("admission_number", "user__username", "user__first_name", "user__last_name")
    ordering = ("user__first_name", "user__last_name", "admission_number")
    list_per_page = 25
    actions = ("export_students_csv",)

    @staticmethod
    def _is_faculty(user):
        return user.is_authenticated and user.role == "FACULTY"

    def has_module_permission(self, request):
        return super().has_module_permission(request) or self._is_faculty(request.user)

    def has_view_permission(self, request, obj=None):
        if is_academic_admin(request.user):
            return True
        if request.user.role == "HOD":
            return obj is None or self._object_is_in_hod_scope(request, obj)
        if not self._is_faculty(request.user):
            return False
        if obj is None:
            return hasattr(request.user, "faculty_profile")
        return obj.semester.subjects.filter(faculty__user=request.user).exists()

    def has_add_permission(self, request):
        return is_academic_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_academic_admin(request.user) or (
            request.user.role == "HOD"
            and (obj is None or self._object_is_in_hod_scope(request, obj))
        )

    def has_delete_permission(self, request, obj=None):
        return is_academic_admin(request.user)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related(
            "user", "department", "program", "semester"
        )
        if self._is_faculty(request.user) and not is_academic_admin(request.user):
            return queryset.filter(
                semester__subjects__faculty__user=request.user
            ).distinct()
        if request.user.role == "HOD" and not is_academic_admin(request.user):
            return queryset.filter(department__hod=request.user)
        return queryset

    def get_readonly_fields(self, request, obj=None):
        if self._is_faculty(request.user) and not is_academic_admin(request.user):
            return tuple(field.name for field in self.model._meta.concrete_fields)
        if request.user.role == "HOD":
            return ("user", "admission_number")
        return super().get_readonly_fields(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.role == "HOD":
            if db_field.name == "department":
                kwargs["queryset"] = Department.objects.filter(hod=request.user)
            elif db_field.name == "program":
                kwargs["queryset"] = Program.objects.filter(
                    department__hod=request.user
                )
            elif db_field.name == "semester":
                kwargs["queryset"] = Semester.objects.filter(
                    program__department__hod=request.user
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description="Export selected students to CSV", permissions=("view",))
    def export_students_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response.write("\ufeff")
        filename = slugify(queryset.first().program.code if queryset.exists() else "students")
        response["Content-Disposition"] = f'attachment; filename="{filename}-students.csv"'
        writer = csv.writer(response)
        writer.writerow((
            "Serial number", "Student name", "Registration number", "Programme",
            "Semester", "Department", "Account status", "Registration needs review",
        ))
        for student in queryset.select_related("user", "program", "semester", "department"):
            writer.writerow((
                student.source_serial_number or "",
                student.user.get_full_name() or student.user.username,
                student.admission_number,
                student.program.name,
                f"Semester {student.semester.number}",
                student.department.name,
                student.get_status_display(),
                "Yes" if student.registration_review_required else "No",
            ))
        return response


@admin.register(Faculty)
class FacultyAdmin(AcademicAdmin):
    list_display = ("faculty_id", "user", "department", "designation", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("faculty_id", "user__username", "user__first_name", "user__last_name")

    def get_readonly_fields(self, request, obj=None):
        if request.user.role == "HOD" and obj is not None:
            return ("user",)
        return super().get_readonly_fields(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.role == "HOD":
            if db_field.name == "department":
                kwargs["queryset"] = Department.objects.filter(hod=request.user)
            elif db_field.name == "user":
                from accounts.models import User

                kwargs["queryset"] = User.objects.filter(
                    role=User.Role.FACULTY
                ).filter(
                    Q(faculty_profile__isnull=True)
                    | Q(faculty_profile__department__hod=request.user)
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(FacultyDirectoryProfile)
class FacultyDirectoryProfileAdmin(AcademicAdmin):
    list_display = (
        "full_name", "designation", "department_name", "faculty", "account",
        "verified_on", "is_active",
    )
    list_filter = ("department_name", "designation", "is_active", "verified_on")
    search_fields = (
        "full_name", "designation", "department_name", "qualifications",
        "institutional_email",
    )
    readonly_fields = ("created_at", "last_updated_at")


@admin.register(Subject)
class SubjectAdmin(AuditedModelAdmin):
    list_display = (
        "code", "name", "semester", "faculty", "credits", "weekly_hours",
        "subject_type", "is_active",
    )
    list_filter = ("semester__program", "semester__number", "subject_type", "is_active")
    search_fields = ("code", "name", "faculty__user__first_name", "faculty__user__last_name")
    ordering = ("semester__program__code", "semester__number", "code")
    actions = ("archive_subjects", "delete_selected")

    @staticmethod
    def _is_faculty(user):
        return user.is_authenticated and user.role == "FACULTY"

    def has_module_permission(self, request):
        return is_academic_admin(request.user) or self._is_faculty(request.user) or (
            request.user.role == "HOD"
            and request.user.headed_departments.exists()
        )

    def has_view_permission(self, request, obj=None):
        if is_academic_admin(request.user):
            return True
        if request.user.role == "HOD":
            return obj is None or can_manage_department(
                request.user, obj.semester.program.department
            )
        if not self._is_faculty(request.user):
            return False
        return obj is None or (
            obj.faculty is not None and obj.faculty.user_id == request.user.id
        )

    def has_add_permission(self, request):
        return is_academic_admin(request.user) or (
            request.user.role == "HOD"
            and request.user.headed_departments.exists()
        )

    def has_change_permission(self, request, obj=None):
        if is_academic_admin(request.user):
            return True
        if request.user.role == "HOD":
            return obj is None or can_manage_department(
                request.user, obj.semester.program.department
            )
        return self._is_faculty(request.user) and (
            obj is None or (
                obj.faculty is not None and obj.faculty.user_id == request.user.id
            )
        )

    def has_delete_permission(self, request, obj=None):
        return is_academic_admin(request.user)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related(
            "semester__program", "faculty__user"
        )
        if self._is_faculty(request.user) and not is_academic_admin(request.user):
            return queryset.filter(faculty__user=request.user)
        if request.user.role == "HOD" and not is_academic_admin(request.user):
            return queryset.filter(semester__program__department__hod=request.user)
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.role == "HOD":
            if db_field.name == "semester":
                kwargs["queryset"] = Semester.objects.filter(
                    program__department__hod=request.user
                )
            elif db_field.name == "faculty":
                kwargs["queryset"] = Faculty.objects.filter(
                    department__hod=request.user
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if request.user.role == "HOD" and not can_manage_department(
            request.user, obj.semester.program.department
        ):
            raise PermissionDenied
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if self._is_faculty(request.user) and not is_academic_admin(request.user):
            return [field for field in fields if field not in {"faculty", "semester"}]
        return fields

    @admin.action(
        description="Archive selected subjects",
        permissions=("delete",),
    )
    def archive_subjects(self, request, queryset):
        with transaction.atomic():
            for subject in queryset:
                previous = capture_snapshot(subject)
                subject.is_active = False
                subject.save(update_fields=("is_active",))
                record_update(
                    request,
                    subject,
                    previous,
                    "Archived by an administrator.",
                )


admin.site.register(AuditLog, AuditLogAdmin)
