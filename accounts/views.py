import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from academics.audit import (
    audits_for_departments,
    capture_snapshot,
    record_create,
    record_sensitive_update,
    record_update,
)
from academics.models import (
    AcademicYear,
    AuditLog,
    FacultyDirectoryProfile,
    Student,
    Faculty,
    Department,
    Program,
    Semester,
    Subject,
)
from academics.permissions import is_academic_admin
from .forms import (
    CollegeAuthenticationForm,
    ManagedStudentForm,
    RequiredPasswordChangeForm,
    SubjectUpdateForm,
)


User = get_user_model()

def sign_in(request):
    if request.user.is_authenticated:
        if request.user.must_change_password:
            return redirect("password-change")
        return redirect({
            User.Role.HOD: "hod-dashboard",
            User.Role.FACULTY: "faculty-dashboard",
            User.Role.STUDENT: "student-dashboard",
        }.get(request.user.role, "dashboard"))
    form = CollegeAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if user.must_change_password:
            return redirect("password-change")
        return redirect({
            User.Role.HOD: "hod-dashboard",
            User.Role.FACULTY: "faculty-dashboard",
            User.Role.STUDENT: "student-dashboard",
        }.get(user.role, "dashboard"))
    return render(request, "accounts/login.html", {"form": form})


def faculty_directory(request):
    profiles = FacultyDirectoryProfile.objects.filter(is_active=True).prefetch_related(
        "faculty__subjects__semester__program"
    )
    query = request.GET.get("q", "").strip()
    department = request.GET.get("department", "").strip()
    designation = request.GET.get("designation", "").strip()
    if query:
        profiles = profiles.filter(
            Q(full_name__icontains=query)
            | Q(designation__icontains=query)
            | Q(qualifications__icontains=query)
            | Q(department_name__icontains=query)
        )
    if department:
        profiles = profiles.filter(department_name=department)
    if designation:
        profiles = profiles.filter(designation=designation)
    departments = (
        FacultyDirectoryProfile.objects.filter(is_active=True)
        .order_by("department_name")
        .values_list("department_name", flat=True)
        .distinct()
    )
    designations = (
        FacultyDirectoryProfile.objects.filter(is_active=True)
        .order_by("designation")
        .values_list("designation", flat=True)
        .distinct()
    )
    return render(request, "accounts/faculty_directory.html", {
        "profiles": profiles,
        "query": query,
        "selected_department": department,
        "selected_designation": designation,
        "departments": departments,
        "designations": designations,
    })


def faculty_profile_detail(request, pk):
    profile = get_object_or_404(
        FacultyDirectoryProfile.objects.filter(is_active=True).select_related(
            "account", "faculty__user"
        ).prefetch_related("faculty__subjects__semester__program"),
        pk=pk,
    )
    return render(request, "accounts/faculty_profile.html", {"profile": profile})


@login_required
def dashboard(request):
    if request.user.must_change_password:
        return redirect("password-change")

    role = request.user.role
    is_hod = role == User.Role.HOD
    is_faculty = role == User.Role.FACULTY
    is_staff_view = is_academic_admin(request.user) or is_hod or role == "EXAM"
    departments_qs = Department.objects.filter(is_active=True)
    if is_hod:
        departments_qs = departments_qs.filter(hod=request.user)
    managed_department_ids = departments_qs.values_list("pk", flat=True)

    if is_hod:
        managed_students = Student.objects.filter(department_id__in=managed_department_ids)
        managed_faculty = Faculty.objects.filter(
            department_id__in=managed_department_ids,
        ).select_related("user", "department").prefetch_related("subjects")
        students = managed_students.filter(status=Student.Status.ACTIVE).count()
        faculty = managed_faculty.filter(is_active=True).count()
        departments = departments_qs.count()
        programs = Program.objects.filter(department_id__in=managed_department_ids, is_active=True).count()
        recent_students = managed_students.select_related(
            "user", "department", "program"
        ).order_by("-created_at")[:6]
        department_data = list(
            departments_qs.annotate(total=Count("student")).values("name", "total")
        )
    elif is_academic_admin(request.user) or role == "EXAM":
        students = Student.objects.filter(status=Student.Status.ACTIVE).count()
        faculty = Faculty.objects.filter(is_active=True).count()
        departments = departments_qs.count()
        programs = Program.objects.filter(is_active=True).count()
        recent_students = Student.objects.select_related(
            "user", "department", "program"
        ).order_by("-created_at")[:6]
        department_data = list(
            departments_qs.annotate(total=Count("student"))
            .values("name", "total").order_by("-total")[:6]
        )
        managed_students = Student.objects.none()
    elif is_faculty:
        managed_students = _managed_students(request.user)
        students = managed_students.filter(status=Student.Status.ACTIVE).count()
        try:
            faculty_profile = request.user.faculty_profile
        except Faculty.DoesNotExist:
            faculty_profile = None
        faculty = 1 if faculty_profile and faculty_profile.is_active else 0
        departments = 1 if faculty_profile and faculty_profile.department.is_active else 0
        programs = managed_students.values("program_id").distinct().count()
        recent_students = managed_students.select_related(
            "user", "department", "program"
        ).order_by("-created_at")[:6]
        department_data = []
    else:
        students = Student.objects.filter(user=request.user).count()
        faculty = 0
        departments = 0
        programs = 0
        recent_students = []
        department_data = []
        managed_students = Student.objects.none()
    subjects = Subject.objects.select_related(
        "semester__program", "faculty__user"
    ).filter(is_active=True)
    if request.user.role == "STUDENT" and not is_academic_admin(request.user):
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            subjects = subjects.none()
        else:
            subjects = subjects.filter(semester=student.semester)
    elif request.user.role == "FACULTY" and not is_academic_admin(request.user):
        try:
            faculty_profile = request.user.faculty_profile
        except Faculty.DoesNotExist:
            subjects = subjects.none()
        else:
            subjects = subjects.filter(faculty=faculty_profile)
    elif is_hod:
        subjects = subjects.filter(
            semester__program__department__in=departments_qs
        )
    subject_semesters = subjects.values(
        "semester_id", "semester__name", "semester__number", "semester__program__code"
    ).distinct()
    principal_profile = None
    if request.user.role == "SUPER_ADMIN" or request.user.is_superuser:
        principal_profile = FacultyDirectoryProfile.objects.filter(
            account=request.user,
            is_active=True,
        ).first()
    semester_student_data = []
    if is_hod:
        semester_student_data = list(
            managed_students.values(
                "semester__program__code", "semester__number"
            ).annotate(total=Count("pk")).order_by(
                "semester__program__code", "semester__number"
            )
        )
    faculty_profile = getattr(request.user, "faculty_profile", None) if is_faculty else None
    hod_profile = getattr(request.user, "faculty_profile", None) if is_hod else None
    teacher_students = managed_students if is_faculty else Student.objects.none()
    if is_faculty:
        semester_student_data = list(
            teacher_students.values(
                "semester__program__code", "semester__number"
            ).annotate(total=Count("pk")).order_by(
                "semester__program__code", "semester__number"
            )
        )
    if is_hod:
        recent_activities = audits_for_departments(departments_qs)[:8]
    else:
        recent_activities = AuditLog.objects.filter(actor=request.user).order_by(
            "-timestamp"
        )[:8]
    account_counts = {
        "active": User.objects.filter(is_active=True, role__in=(User.Role.STUDENT, User.Role.FACULTY)).count(),
        "inactive": User.objects.filter(is_active=False, role__in=(User.Role.STUDENT, User.Role.FACULTY)).count(),
    }
    if is_hod:
        account_counts["active"] = User.objects.filter(
            is_active=True
        ).filter(
            Q(student_profile__department_id__in=managed_department_ids)
            | Q(faculty_profile__department_id__in=managed_department_ids)
        ).distinct().count()
        account_counts["inactive"] = User.objects.filter(
            is_active=False
        ).filter(
            Q(student_profile__department_id__in=managed_department_ids)
            | Q(faculty_profile__department_id__in=managed_department_ids)
        ).distinct().count()
    return render(request, "accounts/dashboard.html", {
        "students_count": students, "faculty_count": faculty, "departments_count": departments,
        "programs_count": programs, "recent_students": recent_students,
        "department_data": department_data, "staff_view": is_staff_view,
        "subjects": subjects, "subject_semesters": subject_semesters,
        "can_manage_academic_records": is_academic_admin(request.user),
        "principal_profile": principal_profile,
        "is_hod": is_hod,
        "is_faculty": is_faculty,
        "hod_departments": departments_qs,
        "hod_faculty": managed_faculty if is_hod else Faculty.objects.none(),
        "semester_student_data": semester_student_data,
        "account_counts": account_counts,
        "teacher_profile": faculty_profile,
        "hod_profile": hod_profile,
        "teacher_students": teacher_students,
        "recent_activities": recent_activities,
        "teacher_semester_student_data": semester_student_data if is_faculty else [],
        "dashboard_url": {
            User.Role.HOD: "hod-dashboard",
            User.Role.FACULTY: "faculty-dashboard",
            User.Role.STUDENT: "student-dashboard",
        }.get(role, "dashboard"),
    })


@login_required
def role_dashboard(request, role):
    if request.user.role != role:
        raise PermissionDenied
    return dashboard(request)


def _managed_semesters(user):
    if user.role == User.Role.HOD:
        return Semester.objects.filter(program__department__hod=user)
    if user.role == User.Role.FACULTY:
        return Semester.objects.filter(
            subjects__faculty__user=user,
            subjects__is_active=True,
        ).distinct()
    return Semester.objects.none()


def _managed_students(user):
    return Student.objects.filter(
        semester__in=_managed_semesters(user)
    ).select_related("user", "department", "program", "academic_year", "semester")


def _can_manage_students(user):
    return user.role in {User.Role.HOD, User.Role.FACULTY}


@login_required
def manage_students(request):
    if request.user.must_change_password:
        return redirect("password-change")
    if not _can_manage_students(request.user):
        raise PermissionDenied
    students = _managed_students(request.user).order_by(
        "user__last_name", "user__first_name", "admission_number"
    )
    query = request.GET.get("q", "").strip()
    if query:
        students = students.filter(
            Q(admission_number__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query)
        )
    one_time_credentials = request.session.pop("new_student_credentials", None)
    return render(request, "accounts/managed_students.html", {
        "students": students,
        "query": query,
        "can_add_students": _can_manage_students(request.user),
        "one_time_credentials": one_time_credentials,
    })


def _student_form(request, instance=None):
    if not _can_manage_students(request.user):
        raise PermissionDenied
    semesters = _managed_semesters(request.user)
    form = ManagedStudentForm(
        request.POST or None,
        instance=instance,
        allowed_semesters=semesters,
    )
    return form


@login_required
@require_http_methods(["GET", "POST"])
def add_managed_student(request):
    if request.user.must_change_password:
        return redirect("password-change")
    form = _student_form(request)
    if request.method == "POST" and form.is_valid():
        admission_number = form.cleaned_data["admission_number"]
        if User.objects.filter(username=admission_number).exists():
            form.add_error(
                "admission_number",
                "An account already uses this username. Ask an administrator to verify and link it.",
            )
        else:
            temporary_password = secrets.token_urlsafe(18)
            with transaction.atomic():
                user = User(
                    username=admission_number,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    phone=form.cleaned_data["phone"],
                    role=User.Role.STUDENT,
                    must_change_password=True,
                )
                user.set_password(temporary_password)
                user.save()
                student = form.save(commit=False)
                student.user = user
                student.admission_number = admission_number
                student.save()
                record_create(
                    request,
                    user,
                    "Student login created by an authorized academic user.",
                )
                record_create(
                    request,
                    student,
                    "Student record created by an authorized academic user.",
                )
            request.session["new_student_credentials"] = {
                "username": admission_number,
                "temporary_password": temporary_password,
            }
            messages.success(
                request,
                "Student created. Copy the temporary password now; it will be shown only once.",
            )
            return redirect("managed-students")
    return render(request, "accounts/managed_student_form.html", {
        "form": form,
        "title": "Add student",
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_managed_student(request, pk):
    if request.user.must_change_password:
        return redirect("password-change")
    student = get_object_or_404(_managed_students(request.user), pk=pk)
    previous_student = capture_snapshot(student)
    previous_user = capture_snapshot(student.user)
    form = _student_form(request, student)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            student = form.save(commit=False)
            student.save()
            student.user.first_name = form.cleaned_data["first_name"]
            student.user.last_name = form.cleaned_data["last_name"]
            student.user.phone = form.cleaned_data["phone"]
            student.user.save(update_fields=("first_name", "last_name", "phone"))
            reason = request.POST.get("change_reason", "")
            record_update(request, student, previous_student, reason)
            record_update(request, student.user, previous_user, reason)
        messages.success(request, "Student details updated.")
        return redirect("managed-students")
    return render(request, "accounts/managed_student_form.html", {
        "form": form,
        "title": "Edit student",
        "student": student,
    })


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    form = RequiredPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        with transaction.atomic():
            user.must_change_password = False
            user.save(update_fields=("password", "must_change_password"))
            record_sensitive_update(
                request,
                user,
                "password",
                "Changed password through the account security page.",
            )
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("dashboard")
    return render(request, "accounts/password_change.html", {
        "form": form,
        "required_change": request.user.must_change_password,
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_subject(request, pk):
    subject = get_object_or_404(
        Subject.objects.select_related("faculty__user"),
        pk=pk,
    )
    can_manage = is_academic_admin(request.user)
    is_assigned_faculty = (
        request.user.role == "FACULTY"
        and subject.faculty is not None
        and subject.faculty.user_id == request.user.id
    )
    if not (can_manage or is_assigned_faculty):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    original_values = capture_snapshot(subject)
    form = SubjectUpdateForm(
        request.POST or None,
        instance=subject,
        allow_semester=can_manage,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            subject = form.save()
            record_update(
                request,
                subject,
                original_values,
                request.POST.get("change_reason", ""),
            )
        messages.success(request, "Subject details have been updated.")
        return redirect("dashboard")
    return render(request, "accounts/subject_form.html", {
        "form": form,
        "subject": subject,
    })


@login_required
@require_POST
def sign_out(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")
