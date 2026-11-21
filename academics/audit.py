import json

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django import forms

from .models import (
    AuditLog,
    Faculty,
    Program,
    Semester,
    Student,
    Subject,
)


User = get_user_model()


def audits_for_departments(departments):
    department_ids = departments.values("pk")
    student_ids = Student.objects.filter(
        department_id__in=department_ids
    ).values("pk")
    faculty_ids = Faculty.objects.filter(
        department_id__in=department_ids
    ).values("pk")
    program_ids = Program.objects.filter(
        department_id__in=department_ids
    ).values("pk")
    semester_ids = Semester.objects.filter(
        program_id__in=program_ids
    ).values("pk")
    subject_ids = Subject.objects.filter(
        semester_id__in=semester_ids
    ).values("pk")
    user_ids = User.objects.filter(
        Q(student_profile__department_id__in=department_ids)
        | Q(faculty_profile__department_id__in=department_ids)
        | Q(headed_departments__in=departments)
    ).values("pk")
    return AuditLog.objects.filter(
        Q(record_type="academics.department", object_id__in=department_ids)
        | Q(record_type="academics.program", object_id__in=program_ids)
        | Q(record_type="academics.semester", object_id__in=semester_ids)
        | Q(record_type="academics.student", object_id__in=student_ids)
        | Q(record_type="academics.faculty", object_id__in=faculty_ids)
        | Q(record_type="academics.subject", object_id__in=subject_ids)
        | Q(record_type="accounts.user", object_id__in=user_ids)
    ).order_by("-timestamp", "-pk")


def capture_snapshot(instance):
    return {
        field.name: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if field.name not in {"password", "last_login"}
    }


def _capture_many_to_many(instance):
    return {
        field.name: list(
            getattr(instance, field.name).order_by("pk").values_list("pk", flat=True)
        )
        for field in instance._meta.many_to_many
    }


def _json_value(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def _record_role(instance):
    if hasattr(instance, "role"):
        return instance.role
    if isinstance(instance, Student):
        return "STUDENT"
    if isinstance(instance, Faculty):
        return "FACULTY"
    return ""


def _create_audit_entry(
    request, instance, action, changes, reason="", record_repr=None, record_role=None
):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        record_type=f"{instance._meta.app_label}.{instance._meta.model_name}",
        record_role=record_role if record_role is not None else _record_role(instance),
        record_repr=(record_repr if record_repr is not None else str(instance))[:255],
        changes=_json_value(changes),
        reason=reason.strip(),
    )


def record_update(request, instance, previous, reason=""):
    current = capture_snapshot(instance)
    changes = {
        key: {
            "old": _json_value(previous[key]),
            "new": _json_value(value),
        }
        for key, value in current.items()
        if previous.get(key) != value
    }
    if changes:
        _create_audit_entry(
            request, instance, AuditLog.Action.UPDATE, changes, reason
        )


def record_create(request, instance, reason=""):
    current = capture_snapshot(instance)
    changes = {
        key: {"old": None, "new": _json_value(value)}
        for key, value in current.items()
        if key not in {"password", "last_login"}
    }
    _create_audit_entry(
        request, instance, AuditLog.Action.CREATE, changes, reason
    )


def record_sensitive_update(request, instance, field_name, reason):
    _create_audit_entry(
        request,
        instance,
        AuditLog.Action.UPDATE,
        {field_name: {"old": "[redacted]", "new": "[redacted]"}},
        reason,
    )


class AuditedModelAdmin(admin.ModelAdmin):
    audit_excluded_fields = ()

    def get_form(self, request, obj=None, **kwargs):
        default_form = self.form if obj is not None else getattr(self, "add_form", self.form)
        form_class = kwargs.get("form", default_form)
        if "change_reason" not in form_class.base_fields:
            kwargs["form"] = type(
                f"{form_class.__name__}WithAuditReason",
                (form_class,),
                {
                    "change_reason": forms.CharField(
                        label="Reason for change",
                        required=False,
                        widget=forms.Textarea(attrs={"rows": 2}),
                    )
                },
            )
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "change_reason" not in fields:
            fields.append("change_reason")
        return fields

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            previous = None
            previous_relations = {}
            if change:
                previous_obj = self.model._default_manager.filter(pk=obj.pk).first()
                if previous_obj is not None:
                    previous = capture_snapshot(previous_obj)
                    previous_relations = _capture_many_to_many(previous_obj)
            request._audit_relation_state = (
                self.model,
                str(obj.pk) if change else None,
                previous_relations,
                form.cleaned_data.get("change_reason", ""),
            )
            super().save_model(request, obj, form, change)
            if previous is None:
                current = capture_snapshot(obj)
                changes = {
                    key: {"old": None, "new": _json_value(value)}
                    for key, value in current.items()
                    if key not in self.audit_excluded_fields
                }
                action = AuditLog.Action.CREATE
            else:
                record_update(
                    request,
                    obj,
                    previous,
                    form.cleaned_data.get("change_reason", ""),
                )
                return
            if changes:
                _create_audit_entry(
                    request, obj, action, changes,
                    form.cleaned_data.get("change_reason", ""),
                )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        state = getattr(request, "_audit_relation_state", None)
        if state is None:
            return
        model, object_id, previous_relations, reason = state
        obj = form.instance
        if model is not obj.__class__ or object_id not in {None, str(obj.pk)}:
            return
        current_relations = _capture_many_to_many(obj)
        changes = {
            field_name: {
                "old": previous_relations.get(field_name, []),
                "new": values,
            }
            for field_name, values in current_relations.items()
            if previous_relations.get(field_name, []) != values
        }
        if changes:
            _create_audit_entry(
                request, obj, AuditLog.Action.UPDATE, changes, reason
            )
        del request._audit_relation_state

    def delete_model(self, request, obj):
        before = capture_snapshot(obj)
        record_repr = str(obj)
        role = _record_role(obj)
        with transaction.atomic():
            super().delete_model(request, obj)
            _create_audit_entry(
                request,
                obj,
                AuditLog.Action.DELETE,
                {
                    key: {"old": _json_value(value), "new": None}
                    for key, value in before.items()
                },
                record_repr=record_repr,
                record_role=role,
            )

    def delete_queryset(self, request, queryset):
        entries = [
            (obj, capture_snapshot(obj), str(obj), _record_role(obj))
            for obj in queryset
        ]
        with transaction.atomic():
            super().delete_queryset(request, queryset)
            for obj, before, record_repr, role in entries:
                _create_audit_entry(
                    request,
                    obj,
                    AuditLog.Action.DELETE,
                    {
                        key: {"old": _json_value(value), "new": None}
                        for key, value in before.items()
                    },
                    record_repr=record_repr,
                    record_role=role,
                )


class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp", "actor", "action", "record_type", "record_repr", "reason",
    )
    list_filter = ("action", "record_type", "timestamp")
    search_fields = ("record_repr", "record_type", "object_id", "actor__username")
    readonly_fields = (
        "actor", "timestamp", "action", "content_type", "object_id", "record_type",
        "record_role", "record_repr", "changes", "reason",
    )
    date_hierarchy = "timestamp"

    def has_module_permission(self, request):
        from .permissions import is_academic_admin

        return is_academic_admin(request.user) or (
            request.user.is_authenticated
            and request.user.role == "HOD"
            and request.user.headed_departments.exists()
        )

    def has_view_permission(self, request, obj=None):
        from .permissions import is_academic_admin

        if is_academic_admin(request.user):
            return True
        if not (
            request.user.is_authenticated
            and request.user.role == "HOD"
            and request.user.headed_departments.exists()
        ):
            return False
        return obj is None or self.get_queryset(request).filter(pk=obj.pk).exists()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser or request.user.role in {
            "SUPER_ADMIN", "ADMIN", "PRINCIPAL"
        }:
            return queryset
        if not request.user.is_authenticated or request.user.role != "HOD":
            return queryset.none()
        return audits_for_departments(request.user.headed_departments.all())

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
