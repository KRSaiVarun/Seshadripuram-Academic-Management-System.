import csv
import os
import secrets
import tempfile
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.authtoken.models import Token

from accounts.models import User
from academics.models import AuditLog, Student


class Command(BaseCommand):
    help = (
        "Set one-time temporary passwords for student accounts and write a private "
        "credential CSV."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output-path", required=True)
        parser.add_argument("--expected-count", type=int, default=45)

    def handle(self, *args, **options):
        output_path = Path(options["output_path"]).expanduser().resolve()
        expected_count = options["expected_count"]
        if expected_count < 1:
            raise CommandError("--expected-count must be greater than zero.")
        if not output_path.parent.is_dir():
            raise CommandError("The credential export directory must already exist.")
        if os.path.lexists(output_path):
            raise CommandError("The credential export file already exists.")

        students = list(
            Student.objects.select_related("user").order_by("admission_number")
        )
        if len(students) != expected_count:
            raise CommandError(
                f"Expected {expected_count} student records; found {len(students)}."
            )
        if any(student.user.role != User.Role.STUDENT for student in students):
            raise CommandError("Every linked account must have the Student role.")
        if any(student.user.has_usable_password() for student in students):
            raise CommandError(
                "At least one student account already has a usable password; "
                "no passwords were changed."
            )

        credentials = [
            (student, secrets.token_urlsafe(24))
            for student in students
        ]
        temporary_path = None
        committed = False
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                dir=output_path.parent,
                delete=False,
            ) as export_file:
                temporary_path = Path(export_file.name)
                writer = csv.writer(export_file)
                writer.writerow(
                    (
                        "registration_number",
                        "username",
                        "student_name",
                        "temporary_password",
                    )
                )
                for student, password in credentials:
                    writer.writerow(
                        (
                            student.admission_number,
                            student.user.username,
                            student.user.get_full_name() or student.user.username,
                            password,
                        )
                    )

            if temporary_path is None:
                raise CommandError("Could not create the credential export.")
            content_type = ContentType.objects.get_for_model(User)
            with transaction.atomic():
                for student, password in credentials:
                    user = student.user
                    previous_must_change_password = user.must_change_password
                    user.set_password(password)
                    user.must_change_password = True
                    user.save(update_fields=("password", "must_change_password"))
                    Token.objects.filter(user=user).delete()
                    AuditLog.objects.create(
                        actor=None,
                        action=AuditLog.Action.UPDATE,
                        content_type=content_type,
                        object_id=str(user.pk),
                        record_type="accounts.user",
                        record_role=User.Role.STUDENT,
                        record_repr=str(user)[:255],
                        changes={
                            "password": {
                                "old": "[redacted]",
                                "new": "[redacted]",
                            },
                            "must_change_password": {
                                "old": previous_must_change_password,
                                "new": True,
                            },
                        },
                        reason="One-time initial student password provisioning.",
                    )
            committed = True
            os.rename(temporary_path, output_path)
        except OSError as exc:
            if committed:
                raise CommandError(
                    "Student passwords were updated, but the export could not be "
                    f"finalized. The private temporary file remains at {temporary_path}."
                ) from exc
            raise
        finally:
            if (
                not committed
                and temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink()

        self.stdout.write(
            self.style.SUCCESS(
                f"Provisioned {len(credentials)} student accounts. "
                f"Private credential export: {output_path}"
            )
        )
