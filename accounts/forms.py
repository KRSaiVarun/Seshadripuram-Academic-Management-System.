from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from academics.models import AcademicYear, Student, Subject


class CollegeAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class":"field", "placeholder":"Username", "autocomplete":"username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class":"field", "placeholder":"Password", "autocomplete":"current-password"}))


class RequiredPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field"


class ManagedStudentForm(forms.ModelForm):
    admission_number = forms.CharField(max_length=40)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Student
        fields = (
            "admission_number",
            "first_name",
            "last_name",
            "phone",
            "academic_year",
            "semester",
            "date_of_birth",
            "guardian_name",
            "guardian_phone",
            "address",
            "status",
        )
        widgets = {
            "academic_year": forms.Select(attrs={"class": "field"}),
            "semester": forms.Select(attrs={"class": "field"}),
            "date_of_birth": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "field", "type": "date"},
            ),
            "guardian_name": forms.TextInput(attrs={"class": "field"}),
            "guardian_phone": forms.TextInput(attrs={"class": "field"}),
            "address": forms.Textarea(attrs={"class": "field", "rows": 3}),
            "status": forms.Select(attrs={"class": "field"}),
        }

    def __init__(self, *args, allowed_semesters, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_semesters = allowed_semesters
        self.fields["semester"].queryset = allowed_semesters.select_related(
            "program__department"
        )
        self.fields["academic_year"].queryset = AcademicYear.objects.order_by(
            "-is_current", "-start_date"
        )
        if self.instance and self.instance.pk:
            self.fields["admission_number"].initial = self.instance.admission_number
            self.fields["admission_number"].disabled = True
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["phone"].initial = self.instance.user.phone
        else:
            self.fields["admission_number"].required = True
        self.fields["admission_number"].widget.attrs["class"] = "field"
        self.fields["first_name"].widget.attrs["class"] = "field"
        self.fields["last_name"].widget.attrs["class"] = "field"
        self.fields["phone"].widget.attrs["class"] = "field"

    def clean_semester(self):
        semester = self.cleaned_data["semester"]
        if not self.allowed_semesters.filter(pk=semester.pk).exists():
            raise forms.ValidationError("You cannot manage students in this semester.")
        return semester

    def clean_admission_number(self):
        admission_number = self.cleaned_data["admission_number"].strip()
        if not self.instance.pk and Student.objects.filter(
            admission_number=admission_number
        ).exists():
            raise forms.ValidationError("A student already uses this registration number.")
        return admission_number

    def save(self, commit=True):
        student = super().save(commit=False)
        student.program = student.semester.program
        student.department = student.semester.program.department
        if commit:
            student.save()
        return student


class SubjectUpdateForm(forms.ModelForm):
    def __init__(self, *args, allow_semester=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_semester:
            self.fields.pop("semester")

    class Meta:
        model = Subject
        fields = ("code", "name", "semester", "credits", "weekly_hours", "subject_type")
        widgets = {
            "code": forms.TextInput(attrs={"class": "field"}),
            "name": forms.TextInput(attrs={"class": "field"}),
            "semester": forms.Select(attrs={"class": "field"}),
            "credits": forms.NumberInput(attrs={"class": "field", "min": 1}),
            "weekly_hours": forms.NumberInput(attrs={"class": "field", "min": 1}),
            "subject_type": forms.Select(attrs={"class": "field"}),
        }
