from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from academics.models import Department, Faculty, Program, Semester, Subject


User = get_user_model()


class Command(BaseCommand):
    help = "Create or update the MCA Semester III subjects and their faculty assignments."

    subject_data = (
        ("MCA301T", "Web Technologies", "mca_vijaya_lakshmi", "Vijaya Lakshmi", "", "FAC-MCA-301T", "FACULTY", ""),
        ("MCA302T", "Machine Learning", "mca_bharathi", "Bharathi", "", "FAC-MCA-302T", "FACULTY", ""),
        ("MCA303T", "Cloud Technologies", "mca_deeksha", "Deeksha", "", "FAC-MCA-303T", "FACULTY", ""),
        (
            "MCA301E(b)",
            "Data Analysis and Business Intelligence",
            "mca_rajeshwari",
            "Rajeshwari",
            "Ma'am",
            "FAC-MCA-301EB",
            "HOD",
            "Head of Department",
        ),
    )

    def handle(self, *args, **options):
        department, _ = Department.objects.get_or_create(
            code="CS",
            defaults={
                "name": "Computer Science & Applications",
                "description": "Computer applications and software systems",
            },
        )
        program, _ = Program.objects.get_or_create(
            code="MCA",
            defaults={
                "department": department,
                "name": "Master of Computer Applications",
                "duration_years": 2,
            },
        )
        if program.department_id != department.id:
            department = program.department
        for number in range(1, 5):
            Semester.objects.get_or_create(
                program=program,
                number=number,
                defaults={"name": f"Semester {number}"},
            )
        semester = Semester.objects.get(program=program, number=3)

        department = program.department
        User.objects.filter(faculty_profile__isnull=False, is_staff=False).update(
            is_staff=True
        )
        created_accounts = []
        for code, name, username, first_name, last_name, faculty_id, role, designation in self.subject_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": getattr(User.Role, role),
                    "is_staff": True,
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=("password",))
                created_accounts.append(username)
            changed_fields = []
            if user.first_name != first_name:
                user.first_name = first_name
                changed_fields.append("first_name")
            if user.last_name != last_name:
                user.last_name = last_name
                changed_fields.append("last_name")
            if user.role != getattr(User.Role, role):
                user.role = getattr(User.Role, role)
                changed_fields.append("role")
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append("is_staff")
            if changed_fields:
                user.save(update_fields=changed_fields)

            faculty, _ = Faculty.objects.update_or_create(
                user=user,
                defaults={
                    "faculty_id": faculty_id,
                    "department": department,
                    "designation": designation,
                    "is_active": True,
                },
            )
            subject, _ = Subject.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "semester": semester,
                    "faculty": faculty,
                    "credits": 4,
                    "weekly_hours": 4,
                    "subject_type": Subject.SubjectType.THEORY,
                },
            )
            self.stdout.write(f"{subject.code}: {subject.name} — {user.get_full_name()}")

            if role == "HOD":
                if department.hod_id != user.id:
                    department.hod = user
                    department.save(update_fields=("hod",))

        self.stdout.write(self.style.SUCCESS("MCA Semester III subject data is up to date."))
        if created_accounts:
            self.stdout.write(
                self.style.WARNING(
                    "New accounts have no password set. An administrator must set initial "
                    "passwords before these faculty members can sign in: "
                    + ", ".join(created_accounts)
                )
            )
