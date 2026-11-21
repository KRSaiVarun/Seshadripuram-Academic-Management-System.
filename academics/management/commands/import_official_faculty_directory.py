from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import FacultyDirectoryProfile


User = get_user_model()

SOURCE_URL = "https://www.spmcollege.ac.in/mcom/teaching-faculty"
PRINCIPAL_PHOTO_URL = (
    "https://www.spmcollege.ac.in/mcom/images/anandappa-principal.jpg"
)

DIRECTORY = (
    {
        "full_name": "Maj Dr. Anandappa Iramukhadavar",
        "designation": "Principal",
        "department_name": "College leadership",
        "qualifications": "MBA, MA, M.Phil, Ph.D (D.Litt)",
        "photograph_url": PRINCIPAL_PHOTO_URL,
        "account_role": User.Role.SUPER_ADMIN,
        "verified_fields": (
            "full_name",
            "designation",
            "qualifications",
            "photograph_url",
        ),
    },
    {
        "full_name": "Dr. Bhargavi V. R.",
        "designation": "Professor and Director",
        "department_name": "PG Department of Commerce",
        "qualifications": "M.Com, MBA, M.Phil, PGDCP, Ph.D",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Dr. K. Nagavani",
        "designation": "Associate Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "M.Com, M.Phil, MBA, Ph.D.",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Ms. Reshma B.",
        "designation": "Assistant Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "M.Com., PGDBA",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Mr. Mukund V. Koushik",
        "designation": "Assistant Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "M.Com., MBA, PGDBA",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Mr. Jagtap Amol Pradeep",
        "designation": "Assistant Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "MBA, DHRM",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Ms. Shruthi S",
        "designation": "Assistant Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "M.Com., B.Ed",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
    {
        "full_name": "Mr. Prasad M.L",
        "designation": "Assistant Professor",
        "department_name": "PG Department of Commerce",
        "qualifications": "MBA",
        "verified_fields": ("full_name", "designation", "qualifications"),
    },
)


class Command(BaseCommand):
    help = (
        "Import the verified Seshadripuram College PG Commerce faculty directory "
        "without creating login accounts."
    )

    def handle(self, *args, **options):
        admins = list(
            User.objects.filter(role=User.Role.SUPER_ADMIN).order_by(
                "-is_superuser", "pk"
            )
        )
        if len(admins) > 1:
            raise CommandError(
                "Multiple Super Admin accounts exist; resolve the Principal account "
                "before importing the directory."
            )

        verified_on = timezone.localdate()
        created_count = 0
        updated_count = 0
        linked_count = 0
        with transaction.atomic():
            for entry in DIRECTORY:
                values = {
                    "designation": entry["designation"],
                    "department_name": entry["department_name"],
                    "qualifications": entry["qualifications"],
                    "source_url": SOURCE_URL,
                    "verified_on": verified_on,
                    "verified_fields": list(entry["verified_fields"]),
                    "is_active": True,
                }
                for optional_field in (
                    "professional_profile",
                    "institutional_email",
                    "contact_number",
                    "photograph_url",
                ):
                    if optional_field in entry:
                        values[optional_field] = entry[optional_field]

                if entry.get("account_role") and admins:
                    account = admins[0]
                    values["account"] = account
                    account_values = {
                        "first_name": "Maj Dr. Anandappa",
                        "last_name": "Iramukhadavar",
                        "designation": "Principal",
                        "qualifications": "MBA, MA, M.Phil, Ph.D (D.Litt)",
                        "institution": "Seshadripuram College",
                        "profile_photo_url": PRINCIPAL_PHOTO_URL,
                    }
                    for field_name, value in account_values.items():
                        if getattr(account, field_name) != value:
                            setattr(account, field_name, value)
                    account.save(update_fields=tuple(account_values))

                profile, created = FacultyDirectoryProfile.objects.update_or_create(
                    source_url=SOURCE_URL,
                    full_name=entry["full_name"],
                    defaults=values,
                )
                created_count += int(created)
                updated_count += int(not created)
                linked_count += int(profile.account_id is not None)

        self.stdout.write(self.style.SUCCESS(
            f"Verified profiles: {len(DIRECTORY)}; created: {created_count}; "
            f"updated: {updated_count}; linked existing accounts: {linked_count}; "
            "login accounts created: 0."
        ))
        self.stdout.write(f"Source: {SOURCE_URL}")
        self.stdout.write(f"Verified on: {verified_on.isoformat()}")
        self.stdout.write(
            "No contact details, professional biographies, or unnamed faculty "
            "photographs were imported."
        )
        self.stdout.write(
            "No MCA subject assignments were changed; directory identities were "
            "not confirmed as the currently assigned MCA faculty."
        )
