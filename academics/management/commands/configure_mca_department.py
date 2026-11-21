from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from academics.models import (
    AuditLog,
    Department,
    Faculty,
    Program,
    Semester,
    Student,
    Subject,
)


MCA_REFERENCE = "https://www.spmcollege.ac.in/mca/index"
MCA_DEPARTMENT_NAME = "Master of Computer Applications"
MCA_SUBJECTS = {
    "MCA301T": ("Web Technologies", "FAC-MCA-301T", "Vijaya Lakshmi", ""),
    "MCA302T": ("Machine Learning", "FAC-MCA-302T", "Bharathi", ""),
    "MCA303T": ("Cloud Technologies", "FAC-MCA-303T", "Deeksha", ""),
    "MCA301E(b)": (
        "Data Analysis and Business Intelligence",
        "FAC-MCA-301EB",
        "Rajeshwari",
        "Ma'am",
    ),
}


def _record_configuration_change(instance, changes, reason):
    AuditLog.objects.create(
        actor=None,
        action=AuditLog.Action.UPDATE,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        record_type=f"{instance._meta.app_label}.{instance._meta.model_name}",
        record_role=getattr(instance, "role", ""),
        record_repr=str(instance)[:255],
        changes=changes,
        reason=reason,
    )


class Command(BaseCommand):
    help = (
        "Create the official MCA department and move its existing program, students, "
        "faculty, and HOD assignment without changing academic records."
    )

    def handle(self, *args, **options):
        program_matches = list(
            Program.objects.filter(code__iexact="MCA").select_related("department")
        )
        if len(program_matches) != 1:
            raise CommandError(
                f"Expected exactly one MCA program; found {len(program_matches)}."
            )
        program = program_matches[0]
        if program.name != MCA_DEPARTMENT_NAME:
            raise CommandError(
                f"The MCA program name is unexpected: {program.name!r}."
            )

        department_matches = list(
            Department.objects.filter(code__iexact="MCA")
        )
        if len(department_matches) > 1:
            raise CommandError("Multiple departments already use the MCA code.")
        if Department.objects.filter(
            name__iexact=MCA_DEPARTMENT_NAME
        ).exclude(pk__in=[department.pk for department in department_matches]).exists():
            raise CommandError(
                "A department with the MCA name already exists under a different code."
            )
        source_department = program.department
        if source_department.code not in {"CS", "MCA"}:
            raise CommandError(
                "The MCA program is not associated with the expected CS or MCA department."
            )

        student_records = list(
            Student.objects.filter(program=program).select_related(
                "academic_year", "semester"
            )
        )
        if len(student_records) != 45 or any(
            student.academic_year.name != "2026-27"
            or student.semester.number != 3
            for student in student_records
        ):
            raise CommandError(
                "Expected the existing 45 MCA Semester III students in academic year "
                "2026-27; no records were changed."
            )
        if any(
            student.department_id != source_department.pk
            for student in student_records
        ):
            raise CommandError(
                "MCA students have inconsistent department links; no records were changed."
            )

        subjects = list(
            Subject.objects.filter(semester__program=program).select_related(
                "semester", "faculty__user", "faculty__department"
            )
        )
        if len(subjects) != len(MCA_SUBJECTS):
            raise CommandError(
                f"Expected {len(MCA_SUBJECTS)} MCA subjects; found {len(subjects)}."
            )
        for subject in subjects:
            expected = MCA_SUBJECTS.get(subject.code)
            if expected is None:
                raise CommandError(
                    f"Unexpected MCA subject code {subject.code!r}; no records were changed."
                )
            expected_name, faculty_id, first_name, last_name = expected
            expected_role = (
                User.Role.HOD
                if subject.code == "MCA301E(b)"
                else User.Role.FACULTY
            )
            if (
                subject.name != expected_name
                or subject.semester.number != 3
                or subject.faculty is None
                or subject.faculty.faculty_id != faculty_id
                or subject.faculty.user.role != expected_role
                or subject.faculty.user.first_name != first_name
                or subject.faculty.user.last_name != last_name
                or subject.faculty.department_id != source_department.pk
            ):
                raise CommandError(
                    f"The verified assignment for {subject.code} does not match; "
                    "no records were changed."
                )

        hod_matches = list(
            User.objects.filter(role=User.Role.HOD).select_related("faculty_profile")
        )
        if len(hod_matches) != 1:
            raise CommandError(
                f"Expected one existing HOD account; found {len(hod_matches)}."
            )
        hod = hod_matches[0]
        hod_faculty = getattr(hod, "faculty_profile", None)
        rajeshwari_subject = next(
            subject for subject in subjects if subject.code == "MCA301E(b)"
        )
        if (
            hod.first_name != "Rajeshwari"
            or hod.last_name != "Ma'am"
            or hod_faculty is None
            or hod_faculty.pk != rajeshwari_subject.faculty_id
        ):
            raise CommandError(
                "The existing HOD account is not linked to the verified Rajeshwari MCA "
                "faculty profile; no records were changed."
            )
        if source_department.hod_id not in {None, hod.pk}:
            raise CommandError(
                "The CS department is headed by a different account; no records were changed."
            )

        target_department = (
            department_matches[0] if department_matches else None
        )
        if (
            target_department
            and target_department.hod_id not in {None, hod.pk}
        ):
            raise CommandError(
                "The MCA department is already assigned to a different HOD; "
                "no records were changed."
            )

        reason = "Configure official MCA department and verified assignments."
        with transaction.atomic():
            if target_department is None:
                target_department = Department.objects.create(
                    name=MCA_DEPARTMENT_NAME,
                    code="MCA",
                    department_type=Department.DepartmentType.POSTGRADUATE,
                    official_reference=MCA_REFERENCE,
                    is_active=True,
                )
                AuditLog.objects.create(
                    actor=None,
                    action=AuditLog.Action.CREATE,
                    content_type=ContentType.objects.get_for_model(target_department),
                    object_id=str(target_department.pk),
                    record_type="academics.department",
                    record_repr=str(target_department)[:255],
                    changes={
                        "name": {"old": None, "new": target_department.name},
                        "code": {"old": None, "new": target_department.code},
                        "department_type": {
                            "old": None,
                            "new": target_department.department_type,
                        },
                        "official_reference": {
                            "old": None,
                            "new": target_department.official_reference,
                        },
                    },
                    reason=reason,
                )
            elif target_department.name != MCA_DEPARTMENT_NAME:
                raise CommandError(
                    "The existing MCA department has a different name; no records were changed."
                )
            else:
                department_changes = {}
                if (
                    target_department.department_type
                    != Department.DepartmentType.POSTGRADUATE
                ):
                    department_changes["department_type"] = {
                        "old": target_department.department_type,
                        "new": Department.DepartmentType.POSTGRADUATE,
                    }
                    target_department.department_type = (
                        Department.DepartmentType.POSTGRADUATE
                    )
                if target_department.official_reference != MCA_REFERENCE:
                    department_changes["official_reference"] = {
                        "old": target_department.official_reference,
                        "new": MCA_REFERENCE,
                    }
                    target_department.official_reference = MCA_REFERENCE
                if not target_department.is_active:
                    department_changes["is_active"] = {
                        "old": False,
                        "new": True,
                    }
                    target_department.is_active = True
                if department_changes:
                    target_department.save(
                        update_fields=tuple(department_changes.keys())
                    )
                    _record_configuration_change(
                        target_department, department_changes, reason
                    )

            if source_department.pk != target_department.pk:
                source_hod_id = source_department.hod_id
                source_department.hod = None
                source_department.save(update_fields=("hod",))
                _record_configuration_change(
                    source_department,
                    {"hod": {"old": source_hod_id, "new": None}},
                    reason,
                )

                program.department = target_department
                program.save(update_fields=("department",))
                _record_configuration_change(
                    program,
                    {
                        "department": {
                            "old": source_department.pk,
                            "new": target_department.pk,
                        }
                    },
                    reason,
                )

                faculty_ids = {subject.faculty_id for subject in subjects}
                for faculty in Faculty.objects.filter(pk__in=faculty_ids):
                    faculty.department = target_department
                    faculty.save(update_fields=("department",))
                    _record_configuration_change(
                        faculty,
                        {
                            "department": {
                                "old": source_department.pk,
                                "new": target_department.pk,
                            }
                        },
                        reason,
                    )

                for student in student_records:
                    student.department = target_department
                    student.save(update_fields=("department",))
                    _record_configuration_change(
                        student,
                        {
                            "department": {
                                "old": source_department.pk,
                                "new": target_department.pk,
                            }
                        },
                        reason,
                    )

            old_target_hod_id = target_department.hod_id
            if old_target_hod_id != hod.pk:
                target_department.hod = hod
                target_department.save(update_fields=("hod",))
                _record_configuration_change(
                    target_department,
                    {"hod": {"old": old_target_hod_id, "new": hod.pk}},
                    reason,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Configured MCA department; preserved four Semester III subjects and "
                "45 student records; assigned the existing Rajeshwari HOD account."
            )
        )
