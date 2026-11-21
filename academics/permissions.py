from .models import Department


ACADEMIC_ADMIN_ROLES = {"SUPER_ADMIN", "ADMIN", "PRINCIPAL"}


def is_academic_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in ACADEMIC_ADMIN_ROLES
    )


def managed_departments(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.role in ACADEMIC_ADMIN_ROLES:
        return None
    if user.role == "HOD":
        return user.headed_departments.all()
    return Department.objects.none()


def can_manage_department(user, department):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role in ACADEMIC_ADMIN_ROLES:
        return True
    return user.role == "HOD" and user.headed_departments.filter(
        pk=department.pk
    ).exists()
