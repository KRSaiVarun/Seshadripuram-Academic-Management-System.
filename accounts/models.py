from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "College Admin"
        PRINCIPAL = "PRINCIPAL", "Principal"
        HOD = "HOD", "HOD"
        FACULTY = "FACULTY", "Faculty"
        STUDENT = "STUDENT", "Student"
        EXAM = "EXAM", "Examination Department"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    qualifications = models.CharField(max_length=255, blank=True)
    institution = models.CharField(max_length=180, blank=True)
    profile_photo_url = models.URLField(blank=True)
    must_change_password = models.BooleanField(default=False)
    initial_password_provisioned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != self.Role.SUPER_ADMIN:
            self.role = self.Role.SUPER_ADMIN
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "role"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
