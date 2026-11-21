from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from academics.models import Student, Faculty, Department, Program, Semester
from academics.permissions import is_academic_admin

@api_view(["POST"])
@permission_classes([AllowAny])
def desktop_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({"detail": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)
    if user.must_change_password:
        return Response(
            {
                "detail": (
                    "Change your password through the web sign-in page before "
                    "using the desktop app."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key, "username": user.username,
        "full_name": user.get_full_name() or user.username,
        "role": user.get_role_display(),
    })

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def desktop_summary(request):
    user = request.user
    if user.must_change_password:
        return Response(
            {
                "detail": (
                    "Change your password through the web sign-in page before "
                    "using the desktop app."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    staff = is_academic_admin(user) or user.role == "EXAM"
    if user.role == "HOD":
        department_ids = user.headed_departments.values("pk")
        managed_students = Student.objects.filter(department_id__in=department_ids)
        managed_faculty = Faculty.objects.filter(department_id__in=department_ids)
        students_count = managed_students.filter(status="ACTIVE").count()
        faculty_count = managed_faculty.filter(is_active=True).count()
        departments_count = Department.objects.filter(hod=user, is_active=True).count()
        programs_count = Program.objects.filter(
            department_id__in=department_ids,
            is_active=True,
        ).count()
    elif user.role == "FACULTY":
        semesters = Semester.objects.filter(
            subjects__faculty__user=user,
            subjects__is_active=True,
        )
        students_count = Student.objects.filter(
            semester__in=semesters,
            status="ACTIVE",
        ).distinct().count()
        faculty_count = Faculty.objects.filter(user=user, is_active=True).count()
        departments_count = Faculty.objects.filter(
            user=user,
            is_active=True,
            department__is_active=True,
        ).values("department_id").distinct().count()
        programs_count = Student.objects.filter(
            semester__in=semesters
        ).values("program_id").distinct().count()
    elif staff:
        students_count = Student.objects.filter(status="ACTIVE").count()
        faculty_count = Faculty.objects.filter(is_active=True).count()
        departments_count = Department.objects.filter(is_active=True).count()
        programs_count = Program.objects.filter(is_active=True).count()
    else:
        students_count = Student.objects.filter(user=user).count()
        faculty_count = 0
        departments_count = 0
        programs_count = 0
    return Response({
        "user": user.get_full_name() or user.username,
        "role": user.get_role_display(),
        "students": students_count,
        "faculty": faculty_count,
        "departments": departments_count,
        "programs": programs_count,
    })
