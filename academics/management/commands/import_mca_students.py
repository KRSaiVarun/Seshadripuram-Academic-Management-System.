from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from academics.models import AcademicYear, Department, Program, Semester, Student


User = get_user_model()


STUDENTS = (
    (1, "Arjun G", "P18GH25S126001"),
    (2, "Ashwini K V", "P18GH25S126008"),
    (3, "Azeem Ullah Khan", "P1GH25S126015"),
    (4, "Bhoomika S Chauhan", "P18GH25S126006"),
    (5, "Bhumika Murali", "P18GH25S126028"),
    (6, "Brijesh", "P18GH25S126036"),
    (7, "Chetan R", "P18GH25S126005"),
    (8, "Deekshith N", "P18GH25S126048"),
    (9, "Hamsa D S", "P18GH25S126030"),
    (10, "Hamsaveni S G", "P18GH25S126043"),
    (11, "Harshitha S", "P18GH25S126029"),
    (12, "Hema A M", "P18GH25S126018"),
    (13, "K Vaishnavi", "P18GH25S126044"),
    (14, "Karthik Anand rao Mirajkar", "P18GH25S126004"),
    (15, "Kavya G", "P18GH25S126025"),
    (16, "Keerthika.J", "P18GH25S126049"),
    (17, "KR Sai Varun", "P18GH25S126010"),
    (18, "Lakshmi M", "P18GH25S126040"),
    (19, "Laya K N", "P18GH25S126056"),
    (20, "Likhitha Bai G", "P18GH25S126023"),
    (21, "M KEERTHIRAJ", "P18GH25S126031"),
    (22, "Meghana P", "P18GH25S126047"),
    (23, "Mohammed Aquil khan", "P18GH25S126011"),
    (24, "Mohan Kumar R", "P18GH25S126033"),
    (25, "Mokshitha C M", "P18GH25S126016"),
    (26, "Pradyumna B C", "P18GH25S126003"),
    (27, "Pramod B A", "P18GH25S126021"),
    (28, "Preethal V Fernandes", "P18GH25S126027"),
    (29, "Pruthvik N", "P18GH25S126041"),
    (30, "Rajesh Jayashankar", "P18GH25S126020"),
    (31, "Ruchitha D C", "P18GH25S126053"),
    (32, "Ruhana Tasneem M", "P18GH25S126013"),
    (33, "Sahana S H", "P18GH25S126051"),
    (34, "Saikeerthana y", "P18GH25S126039"),
    (35, "Sameer Ahmed R", "P18GH25S126055"),
    (36, "Shashidhar swami h h m", "P18GH25S126042"),
    (37, "Shubha R", "P18GH25S126017"),
    (38, "Sri Lakshmi.M", "P18GH25S126019"),
    (39, "Srinivas Kumar R", "P18GH25S126035"),
    (41, "Umme kulsum", "P18GH25S126007"),
    (42, "Vaishnavi B", "P18GH25S126012"),
    (43, "Vikas.r", "P18GH25S126038"),
    (44, "Yamuna D", "P18GH25S126046"),
    (45, "Yashawanth K M", "P18GH25S120645"),
    (46, "Yashwantha M", "P18GH25S126024"),
)

REGISTRATIONS_REQUIRING_REVIEW = {
    "P1GH25S126015",
    "P18GH25S120645",
}

INCOMPLETE_STUDENTS = ((40, "Suprith", "Registration number was not provided."),)


class Command(BaseCommand):
    help = "Import the supplied MCA student roster with verified programme placement."

    def add_arguments(self, parser):
        parser.add_argument("--semester", type=int, required=True)
        parser.add_argument("--academic-year", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            program = Program.objects.select_related("department").get(code="MCA")
            semester = Semester.objects.get(
                program=program,
                number=options["semester"],
            )
            academic_year = AcademicYear.objects.get(name=options["academic_year"])
        except Program.DoesNotExist as exc:
            raise CommandError("MCA programme is missing; create it before importing.") from exc
        except Semester.DoesNotExist as exc:
            raise CommandError(
                f"MCA Semester {options['semester']} is missing; create it before importing."
            ) from exc
        except AcademicYear.DoesNotExist as exc:
            raise CommandError(
                f"Academic year {options['academic_year']!r} does not exist. "
                "Create and verify it before importing."
            ) from exc

        if semester.program_id != program.id:
            raise CommandError("The selected semester does not belong to the MCA programme.")
        if options["dry_run"]:
            self.stdout.write(
                f"Validated {len(STUDENTS)} complete records for MCA Semester "
                f"{semester.number}, {academic_year.name}."
            )
            self._write_pending_summary()
            return

        created_count = 0
        duplicate_count = 0
        conflict_count = 0
        review_count = 0
        for serial_number, name, registration_number in STUDENTS:
            existing_student = Student.objects.filter(
                admission_number=registration_number
            ).first()
            if existing_student:
                duplicate_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped existing registration {registration_number} "
                        f"(source row {serial_number})."
                    )
                )
                continue

            user = User.objects.filter(username=registration_number).first()
            if user:
                conflict_count += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"Skipped {registration_number}: username already exists "
                        "without a matching registration record."
                    )
                )
                continue

            needs_review = registration_number in REGISTRATIONS_REQUIRING_REVIEW
            if options["dry_run"]:
                created_count += 1
                review_count += int(needs_review)
                continue

            try:
                with transaction.atomic():
                    if user is None:
                        user = User(
                            username=registration_number,
                            first_name=name,
                            role=User.Role.STUDENT,
                            is_active=True,
                            is_staff=False,
                        )
                        user.set_unusable_password()
                        user.save()
                    else:
                        user.first_name = name
                        user.last_name = ""
                        user.role = User.Role.STUDENT
                        user.is_active = True
                        user.is_staff = False
                        user.save(update_fields=(
                            "first_name", "last_name", "role", "is_active", "is_staff"
                        ))
                    Student.objects.create(
                        user=user,
                        admission_number=registration_number,
                        source_serial_number=serial_number,
                        registration_review_required=needs_review,
                        department=program.department,
                        program=program,
                        academic_year=academic_year,
                        semester=semester,
                        status=Student.Status.ACTIVE,
                    )
            except IntegrityError:
                duplicate_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped duplicate registration {registration_number} "
                        f"(source row {serial_number})."
                    )
                )
                continue

            created_count += 1
            review_count += int(needs_review)

        self.stdout.write(self.style.SUCCESS(
            f"Imported: {created_count}; duplicates skipped: {duplicate_count}; "
            f"account conflicts skipped: {conflict_count}; registration numbers "
            f"flagged for review: {review_count}."
        ))
        self._write_pending_summary()
        if created_count:
            self.stdout.write(self.style.WARNING(
                "Student accounts were created with unusable passwords. Set initial "
                "passwords through the authorized account administration process."
            ))

    def _write_pending_summary(self):
        self.stdout.write(
            f"Records not imported pending verification: {len(INCOMPLETE_STUDENTS)}."
        )
        for serial_number, name, reason in INCOMPLETE_STUDENTS:
            self.stdout.write(
                self.style.WARNING(f"Row {serial_number}, {name}: {reason}")
            )
