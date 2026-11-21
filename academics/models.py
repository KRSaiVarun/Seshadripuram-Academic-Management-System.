from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Department(models.Model):
    class DepartmentType(models.TextChoices):
        UNDERGRADUATE = "UG", "Undergraduate"
        POSTGRADUATE = "PG", "Postgraduate"

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    department_type = models.CharField(
        max_length=2,
        choices=DepartmentType.choices,
        blank=True,
    )
    official_reference = models.URLField(blank=True)
    hod = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                            on_delete=models.SET_NULL, related_name="headed_departments")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Program(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    duration_years = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="Example: 2026-27")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Semester(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="semesters")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["program", "number"], name="unique_program_semester")]
        ordering = ["program", "number"]

    def __str__(self):
        return f"{self.program.code} - Semester {self.number}"

class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRADUATED = "GRADUATED", "Graduated"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        SUSPENDED = "SUSPENDED", "Suspended"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    admission_number = models.CharField(max_length=40, unique=True)
    source_serial_number = models.PositiveSmallIntegerField(null=True, blank=True)
    registration_review_required = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    guardian_name = models.CharField(max_length=150, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admission_number} - {self.user.get_full_name()}"

class Faculty(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faculty_profile")
    faculty_id = models.CharField(max_length=40, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    designation = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.faculty_id} - {self.user.get_full_name()}"


class FacultyDirectoryProfile(models.Model):
    full_name = models.CharField(max_length=180)
    designation = models.CharField(max_length=120, blank=True)
    department_name = models.CharField(max_length=180, blank=True)
    qualifications = models.CharField(max_length=255, blank=True)
    professional_profile = models.TextField(blank=True)
    photograph_url = models.URLField(blank=True)
    institutional_email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    source_url = models.URLField()
    verified_on = models.DateField()
    verified_fields = models.JSONField(default=list)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_faculty_profile",
    )
    faculty = models.OneToOneField(
        Faculty,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="directory_profile",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("department_name", "full_name")
        constraints = [
            models.UniqueConstraint(
                fields=("source_url", "full_name"),
                name="unique_source_faculty_profile",
            )
        ]

    def __str__(self):
        return self.full_name


class Subject(models.Model):
    class SubjectType(models.TextChoices):
        THEORY = "THEORY", "Theory"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=180)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="subjects")
    faculty = models.ForeignKey(
        Faculty, null=True, blank=True, on_delete=models.SET_NULL, related_name="subjects"
    )
    credits = models.PositiveSmallIntegerField(default=4)
    weekly_hours = models.PositiveSmallIntegerField(default=4)
    subject_type = models.CharField(
        max_length=12, choices=SubjectType.choices, default=SubjectType.THEORY
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["semester__program__code", "semester__number", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Created"
        UPDATE = "UPDATE", "Updated"
        DELETE = "DELETE", "Deleted"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="academic_audit_entries",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=8, choices=Action.choices)
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    object_id = models.CharField(max_length=64)
    record_type = models.CharField(max_length=100)
    record_role = models.CharField(max_length=20, blank=True)
    record_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-timestamp", "-pk")
        indexes = [
            models.Index(fields=("record_type", "object_id")),
            models.Index(fields=("timestamp",)),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.record_type} #{self.object_id}"
