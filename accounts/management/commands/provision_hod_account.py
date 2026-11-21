from getpass import getpass
import secrets

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academics.models import AuditLog


User = get_user_model()


class Command(BaseCommand):
    help = "One-time provisioning of the existing HOD account and initial password."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--initial-password",
            help="Initial password. Omit to enter it securely at the prompt.",
        )
        group.add_argument(
            "--generate-initial-password",
            action="store_true",
            help="Generate a random password and print it once after provisioning.",
        )

    def handle(self, *args, **options):
        initial_password = options["initial_password"]
        generated_password = options["generate_initial_password"]
        if generated_password:
            initial_password = secrets.token_urlsafe(24)
        elif initial_password is None:
            initial_password = getpass("Initial HOD password: ")
            confirmation = getpass("Confirm initial HOD password: ")
            if initial_password != confirmation:
                raise CommandError("The password entries do not match.")
        if not initial_password:
            raise CommandError("The initial password cannot be blank.")

        hods = list(User.objects.filter(role=User.Role.HOD).order_by("pk"))
        if len(hods) != 1:
            raise CommandError(
                f"Expected exactly one existing HOD account; found {len(hods)}."
            )
        hod = hods[0]
        if hod.initial_password_provisioned:
            self.stdout.write(
                self.style.WARNING(
                    "Initial HOD credentials were already provisioned; no changes were made."
                )
            )
            return
        if User.objects.filter(username__iexact="HOD").exclude(pk=hod.pk).exists():
            raise CommandError(
                "The username 'HOD' belongs to another account. No changes were made."
            )
        previous_username = hod.username
        previous_role = hod.role
        with transaction.atomic():
            hod.username = "HOD"
            hod.set_password(initial_password)
            hod.must_change_password = True
            hod.initial_password_provisioned = True
            hod.save(update_fields=(
                "username",
                "password",
                "must_change_password",
                "initial_password_provisioned",
            ))
            AuditLog.objects.create(
                actor=None,
                action=AuditLog.Action.UPDATE,
                content_type=ContentType.objects.get_for_model(hod),
                object_id=str(hod.pk),
                record_type="accounts.user",
                record_role=hod.role,
                record_repr=str(hod),
                changes={
                    "username": {"old": previous_username, "new": "HOD"},
                    "password": {"old": "[redacted]", "new": "[redacted]"},
                    "must_change_password": {"old": False, "new": True},
                    "initial_password_provisioned": {"old": False, "new": True},
                    "role": {"old": previous_role, "new": hod.role},
                },
                reason="One-time initial HOD account provisioning.",
            )

        self.stdout.write(self.style.SUCCESS(
            "Existing HOD account updated. The password is hashed and must be changed at first login."
        ))
        if generated_password:
            self.stdout.write(f"One-time initial HOD password: {initial_password}")
