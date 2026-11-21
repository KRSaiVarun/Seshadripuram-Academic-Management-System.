from django.core.management import call_command
from django.contrib import admin
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from academics.models import (
    AcademicYear,
    AuditLog,
    Department,
    Faculty,
    FacultyDirectoryProfile,
    Program,
    Semester,
    Student,
    Subject,
)
import io
import datetime
import csv
import tempfile

User = get_user_model()

class AcademicSystemIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="testadmin",
            password="Password@123",
            role=User.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
            first_name="Ramesh",
            last_name="Kumar"
        )
        self.ay = AcademicYear.objects.create(
            name="2026-27",
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2027, 5, 31),
            is_current=True
        )
        self.dept = Department.objects.create(name="Computer Science", code="CS")
        self.prog = Program.objects.create(department=self.dept, name="BCA", code="BCA", duration_years=3)
        self.sem = Semester.objects.create(program=self.prog, number=1, name="Semester 1")
        
        self.student_user = User.objects.create_user(
            username="student1", password="Password@123", role=User.Role.STUDENT
        )
        self.student = Student.objects.create(
            user=self.student_user, admission_number="2026-BCA-001",
            department=self.dept, program=self.prog, academic_year=self.ay,
            semester=self.sem, status=Student.Status.ACTIVE
        )

        self.fac_user = User.objects.create_user(
            username="faculty1", password="Password@123", role=User.Role.FACULTY
        )
        self.faculty = Faculty.objects.create(
            user=self.fac_user, faculty_id="FAC-001",
            department=self.dept, designation="Professor"
        )
        self.subject = Subject.objects.create(
            code="BCA101",
            name="Programming Fundamentals",
            semester=self.sem,
            faculty=self.faculty,
        )

    def test_health_check(self):
        resp = self.client.get(reverse("api-health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_desktop_login_and_summary_flow(self):
        # 1. Successful login
        resp = self.client.post(reverse("desktop-login"), {
            "username": "testadmin", "password": "Password@123"
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["token"]
        self.assertTrue(token)

        # 2. Authenticated summary
        sum_resp = self.client.get(
            reverse("desktop-summary"),
            HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(sum_resp.status_code, 200)
        data = sum_resp.json()
        self.assertEqual(data["students"], 1)
        self.assertEqual(data["faculty"], 1)
        self.assertEqual(data["departments"], 1)
        self.assertEqual(data["programs"], 1)

    def test_web_login_and_dashboard_integration(self):
        # Unauthenticated redirects to login
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)

        # Authenticate
        logged_in = self.client.login(username="testadmin", password="Password@123")
        self.assertTrue(logged_in)

        # Dashboard renders with cosmic canvas and live stats
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn("fx-canvas", content)
        self.assertIn("cosmic-engine.js", content)
        self.assertIn('data-count="1"', content)

    def test_invalid_login(self):
        resp = self.client.post(reverse("desktop-login"), {
            "username": "baduser", "password": "wrong"
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_student_dashboard_shows_only_current_semester_subjects(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "BCA101")
        self.assertContains(response, "Programming Fundamentals")
        self.assertNotContains(response, "/admin/academics/student/")
        self.assertNotContains(response, "/admin/academics/department/add/")

    def test_django_superuser_gets_super_admin_dashboard_access(self):
        root = User.objects.create_superuser(
            username="rootadmin",
            email="root@example.test",
            password="Password@123",
        )
        self.assertEqual(root.role, User.Role.SUPER_ADMIN)
        self.client.force_login(root)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "BCA101")
        self.assertContains(response, 'data-count="1"')
        self.assertContains(response, "/admin/academics/auditlog/")

    def test_faculty_dashboard_shows_only_assigned_subjects(self):
        other_user = User.objects.create_user(
            username="faculty2", password="Password@123", role=User.Role.FACULTY
        )
        other_faculty = Faculty.objects.create(
            user=other_user, faculty_id="FAC-002", department=self.dept
        )
        Subject.objects.create(
            code="BCA102", name="Other Course", semester=self.sem, faculty=other_faculty
        )

        self.client.force_login(self.fac_user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "BCA101")
        self.assertNotContains(response, "BCA102")
        self.assertEqual(
            self.client.get(reverse("faculty-dashboard")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("hod-dashboard")).status_code,
            403,
        )

    def test_assigned_faculty_can_edit_subject_but_student_cannot(self):
        other_semester = Semester.objects.create(
            program=self.prog, number=2, name="Semester 2"
        )
        self.client.force_login(self.fac_user)
        edit_url = reverse("subject-edit", args=[self.subject.pk])
        self.assertEqual(self.client.get(edit_url).status_code, 200)
        response = self.client.post(edit_url, {
            "code": self.subject.code,
            "name": self.subject.name,
            "semester": other_semester.pk,
            "credits": 5,
            "weekly_hours": 4,
            "subject_type": Subject.SubjectType.THEORY,
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.credits, 5)
        self.assertEqual(self.subject.semester, self.sem)

        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get(edit_url).status_code, 403)

    def test_hod_can_manage_academic_admin_and_faculty_accounts(self):
        hod = User.objects.create_user(
            username="hod1",
            password="Password@123",
            role=User.Role.HOD,
            is_staff=True,
        )
        self.dept.hod = hod
        self.dept.save(update_fields=("hod",))

        self.client.force_login(hod)
        self.assertEqual(self.client.get("/admin/academics/subject/").status_code, 200)
        add_user_response = self.client.get("/admin/accounts/user/add/")
        self.assertEqual(add_user_response.status_code, 200)
        self.assertContains(add_user_response, "Faculty")
        self.assertNotContains(add_user_response, "Super Admin")

    def test_faculty_admin_access_is_limited_to_assigned_subjects(self):
        self.fac_user.is_staff = True
        self.fac_user.save(update_fields=("is_staff",))
        other_semester = Semester.objects.create(
            program=self.prog, number=2, name="Semester 2"
        )
        other_student_user = User.objects.create_user(
            username="student2", password="Password@123", role=User.Role.STUDENT
        )
        other_student = Student.objects.create(
            user=other_student_user,
            admission_number="2026-BCA-002",
            department=self.dept,
            program=self.prog,
            academic_year=self.ay,
            semester=other_semester,
        )
        self.client.force_login(self.fac_user)

        subjects_response = self.client.get("/admin/academics/subject/")
        self.assertEqual(subjects_response.status_code, 200)
        self.assertContains(subjects_response, "BCA101")
        student_list_response = self.client.get("/admin/academics/student/")
        self.assertEqual(student_list_response.status_code, 200)
        self.assertContains(student_list_response, self.student.admission_number)
        self.assertNotContains(student_list_response, other_student.admission_number)
        self.assertRedirects(
            self.client.get(
                reverse("admin:academics_student_change", args=[other_student.pk])
            ),
            "/admin/",
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:academics_student_change", args=[self.student.pk])
            ).status_code,
            200,
        )

    def test_student_csv_export_includes_source_serial_and_registration(self):
        self.student.source_serial_number = 1
        self.student.save(update_fields=("source_serial_number",))
        self.client.force_login(self.admin)
        response = self.client.post("/admin/academics/student/", {
            "action": "export_students_csv",
            "_selected_action": [str(self.student.pk)],
            "index": "0",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("2026-BCA-001", response.content.decode("utf-8-sig"))

    def test_super_admin_can_edit_existing_student_and_audit_the_change(self):
        self.client.force_login(self.admin)
        url = reverse("admin:academics_student_change", args=[self.student.pk])
        form_response = self.client.get(url)
        self.assertEqual(form_response.status_code, 200)
        form = form_response.context["adminform"].form
        self.assertIn("change_reason", form.fields)

        response = self.client.post(url, {
            "user": self.student_user.pk,
            "admission_number": self.student.admission_number,
            "department": self.dept.pk,
            "program": self.prog.pk,
            "academic_year": self.ay.pk,
            "semester": self.sem.pk,
            "status": Student.Status.ACTIVE,
            "guardian_name": "Updated guardian",
            "guardian_phone": "",
            "address": "",
            "date_of_birth": "",
            "change_reason": "Corrected the guardian details.",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.guardian_name, "Updated guardian")
        entry = AuditLog.objects.get(
            record_type="academics.student",
            object_id=str(self.student.pk),
            action=AuditLog.Action.UPDATE,
        )
        self.assertEqual(entry.actor, self.admin)
        self.assertEqual(entry.reason, "Corrected the guardian details.")
        self.assertEqual(
            entry.changes["guardian_name"],
            {"old": "", "new": "Updated guardian"},
        )
        self.assertIsNone(self.student.date_of_birth)

    def test_student_admin_accepts_local_date_format_and_preserves_student_user(self):
        target_user = User.objects.create_user(
            username="P18GH25S126010",
            password="Password@123",
            role=User.Role.STUDENT,
            first_name="KR Sai",
            last_name="Varun",
        )
        target = Student.objects.create(
            id=17,
            user=target_user,
            admission_number="P18GH25S126010",
            department=self.dept,
            program=self.prog,
            academic_year=self.ay,
            semester=self.sem,
            date_of_birth=datetime.date(2005, 11, 22),
        )
        self.client.force_login(self.admin)
        url = reverse("admin:academics_student_change", args=[target.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        form = get_response.context["adminform"].form
        self.assertEqual(form["date_of_birth"].value(), datetime.date(2005, 11, 22))
        self.assertEqual(form["user"].value(), target_user.pk)
        self.assertContains(get_response, 'value="2005-11-22"')

        invalid_response = self.client.post(url, {
            "user": target_user.pk,
            "admission_number": target.admission_number,
            "department": self.dept.pk,
            "program": self.prog.pk,
            "academic_year": self.ay.pk,
            "semester": self.sem.pk,
            "date_of_birth": "31-02-2005",
            "status": Student.Status.ACTIVE,
            "guardian_name": "",
            "guardian_phone": "",
            "address": "",
            "change_reason": "",
            "_save": "Save",
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFormError(
            invalid_response.context["adminform"].form,
            "date_of_birth",
            "Enter a valid date.",
        )

        valid_response = self.client.post(url, {
            "user": target_user.pk,
            "admission_number": target.admission_number,
            "department": self.dept.pk,
            "program": self.prog.pk,
            "academic_year": self.ay.pk,
            "semester": self.sem.pk,
            "date_of_birth": "23-11-2005",
            "status": Student.Status.ACTIVE,
            "guardian_name": "",
            "guardian_phone": "",
            "address": "",
            "change_reason": "",
            "_save": "Save",
        })
        self.assertEqual(valid_response.status_code, 302)
        target.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(target.date_of_birth, datetime.date(2005, 11, 23))
        self.assertEqual(target.user_id, target_user.pk)
        self.assertEqual(target.admission_number, "P18GH25S126010")
        self.assertEqual(self.student.user_id, self.student_user.pk)
        self.assertEqual(self.student.admission_number, "2026-BCA-001")

    def test_super_admin_can_edit_faculty_profile_and_subject_assignment(self):
        other_user = User.objects.create_user(
            username="faculty2", password="Password@123", role=User.Role.FACULTY
        )
        other_faculty = Faculty.objects.create(
            user=other_user,
            faculty_id="FAC-002",
            department=self.dept,
            designation="Lecturer",
        )
        self.client.force_login(self.admin)
        faculty_url = reverse("admin:academics_faculty_change", args=[self.faculty.pk])
        faculty_response = self.client.post(faculty_url, {
            "user": self.fac_user.pk,
            "faculty_id": self.faculty.faculty_id,
            "department": self.dept.pk,
            "designation": "Senior Professor",
            "joining_date": "",
            "is_active": "on",
            "change_reason": "Updated faculty designation.",
            "_save": "Save",
        })
        self.assertEqual(faculty_response.status_code, 302)
        self.faculty.refresh_from_db()
        self.assertEqual(self.faculty.designation, "Senior Professor")

        subject_url = reverse("admin:academics_subject_change", args=[self.subject.pk])
        subject_response = self.client.post(subject_url, {
            "code": self.subject.code,
            "name": self.subject.name,
            "semester": self.sem.pk,
            "faculty": other_faculty.pk,
            "credits": 5,
            "weekly_hours": 4,
            "subject_type": Subject.SubjectType.THEORY,
            "is_active": "on",
            "change_reason": "Reassigned the subject and corrected credits.",
            "_save": "Save",
        })
        self.assertEqual(subject_response.status_code, 302)
        self.subject.refresh_from_db()
        self.assertEqual(self.subject.faculty, other_faculty)
        self.assertEqual(self.subject.credits, 5)
        subject_entry = AuditLog.objects.get(
            record_type="academics.subject",
            object_id=str(self.subject.pk),
            action=AuditLog.Action.UPDATE,
        )
        self.assertEqual(subject_entry.actor, self.admin)
        self.assertEqual(
            subject_entry.changes["faculty"],
            {"old": self.faculty.pk, "new": other_faculty.pk},
        )
        self.assertEqual(subject_entry.reason, "Reassigned the subject and corrected credits.")

    def test_hod_cannot_view_or_modify_super_admin_account(self):
        hod = User.objects.create_user(
            username="hod2",
            password="Password@123",
            role=User.Role.HOD,
            is_staff=True,
        )
        self.client.force_login(hod)
        url = reverse("admin:accounts_user_change", args=[self.admin.pk])
        self.assertRedirects(
            self.client.get(url),
            "/admin/",
            fetch_redirect_response=False,
        )
        response = self.client.post(url, {
            "username": "testadmin",
            "first_name": "Changed",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, "Ramesh")

    def test_related_academic_records_block_parent_deletion(self):
        department_admin = admin.site._registry[Department]
        request = RequestFactory().post("/admin/academics/department/")
        request.user = self.admin
        self.assertFalse(
            department_admin.has_delete_permission(request, self.dept)
        )
        with self.assertRaises(ProtectedError):
            department_admin.delete_queryset(
                request, Department.objects.filter(pk=self.dept.pk)
            )
        self.assertTrue(Department.objects.filter(pk=self.dept.pk).exists())
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

    def test_archived_subject_is_not_shown_on_student_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.post("/admin/academics/subject/", {
            "action": "archive_subjects",
            "_selected_action": [str(self.subject.pk)],
            "index": "0",
        })
        self.assertEqual(response.status_code, 302)
        self.subject.refresh_from_db()
        self.assertFalse(self.subject.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                record_type="academics.subject",
                object_id=str(self.subject.pk),
                action=AuditLog.Action.UPDATE,
                reason="Archived by an administrator.",
            ).exists()
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, self.subject.code)

    def test_official_faculty_directory_import_is_idempotent_and_preserves_accounts(self):
        self.admin.set_password("PreserveThis@123")
        self.admin.save(update_fields=("password",))
        old_password_hash = self.admin.password
        original_assignment = self.subject.faculty_id
        original_user_count = User.objects.count()

        output = io.StringIO()
        call_command("import_official_faculty_directory", stdout=output)
        self.assertIn("Verified profiles: 8; created: 8; updated: 0", output.getvalue())

        output = io.StringIO()
        call_command("import_official_faculty_directory", stdout=output)
        self.assertIn("created: 0; updated: 8", output.getvalue())
        self.assertEqual(FacultyDirectoryProfile.objects.count(), 8)
        self.assertEqual(User.objects.count(), original_user_count)
        self.subject.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.subject.faculty_id, original_assignment)
        self.assertEqual(self.admin.password, old_password_hash)
        self.assertEqual(self.admin.username, "testadmin")
        self.assertEqual(self.admin.role, User.Role.SUPER_ADMIN)
        self.assertTrue(self.admin.is_superuser)
        self.assertEqual(self.admin.get_full_name(), "Maj Dr. Anandappa Iramukhadavar")
        principal = FacultyDirectoryProfile.objects.get(account=self.admin)
        self.assertEqual(principal.photograph_url, "https://www.spmcollege.ac.in/mcom/images/anandappa-principal.jpg")
        self.assertIsNotNone(principal.verified_on)
        self.assertEqual(
            FacultyDirectoryProfile.objects.get(full_name="Dr. Bhargavi V. R.").department_name,
            "PG Department of Commerce",
        )
        self.assertFalse(
            FacultyDirectoryProfile.objects.exclude(account=self.admin)
            .filter(account__isnull=False).exists()
        )
        self.assertFalse(
            FacultyDirectoryProfile.objects.exclude(photograph_url="")
            .exclude(full_name="Maj Dr. Anandappa Iramukhadavar").exists()
        )

    def test_public_faculty_directory_search_filter_and_profile_page(self):
        call_command("import_official_faculty_directory", stdout=io.StringIO())
        response = self.client.get(reverse("faculty-directory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maj Dr. Anandappa Iramukhadavar")
        self.assertContains(response, "Dr. Bhargavi V. R.")
        self.assertContains(response, "Seshadripuram Educational Trust logo")

        filtered = self.client.get(
            reverse("faculty-directory"),
            {"q": "Bhargavi", "department": "PG Department of Commerce"},
        )
        self.assertContains(filtered, "Dr. Bhargavi V. R.")
        self.assertNotContains(filtered, "Dr. K. Nagavani")

        profile = FacultyDirectoryProfile.objects.get(
            full_name="Maj Dr. Anandappa Iramukhadavar"
        )
        detail = self.client.get(reverse("faculty-profile", args=[profile.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "MBA, MA, M.Phil, Ph.D (D.Litt)")
        self.assertContains(detail, profile.source_url)

    def test_admin_can_edit_and_audit_official_faculty_profile(self):
        call_command("import_official_faculty_directory", stdout=io.StringIO())
        profile = FacultyDirectoryProfile.objects.get(full_name="Dr. Bhargavi V. R.")
        self.client.force_login(self.admin)
        url = reverse("admin:academics_facultydirectoryprofile_change", args=[profile.pk])
        response = self.client.post(url, {
            "full_name": profile.full_name,
            "designation": "Professor and Director",
            "department_name": profile.department_name,
            "qualifications": "M.Com, MBA, M.Phil, PGDCP, Ph.D",
            "professional_profile": "Verified administrator correction",
            "photograph_url": "",
            "institutional_email": "",
            "contact_number": "",
            "source_url": profile.source_url,
            "verified_on": profile.verified_on.isoformat(),
            "verified_fields": '["full_name", "designation"]',
            "account": "",
            "faculty": "",
            "is_active": "on",
            "change_reason": "Corrected the verified profile text.",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.professional_profile, "Verified administrator correction")
        entry = AuditLog.objects.get(
            record_type="academics.facultydirectoryprofile",
            object_id=str(profile.pk),
            action=AuditLog.Action.UPDATE,
        )
        self.assertEqual(entry.actor, self.admin)
        self.assertEqual(entry.reason, "Corrected the verified profile text.")

    def test_mca_roster_import_is_idempotent_and_skips_incomplete_student(self):
        mca = Program.objects.create(
            department=self.dept,
            name="Master of Computer Applications",
            code="MCA",
            duration_years=2,
        )
        Semester.objects.create(program=mca, number=3, name="Semester 3")

        output = io.StringIO()
        call_command(
            "import_mca_students",
            semester=3,
            academic_year="2026-27",
            stdout=output,
        )
        self.assertEqual(
            Student.objects.filter(program=mca, semester__number=3).count(), 45
        )
        self.assertIn("Imported: 45", output.getvalue())
        self.assertIn("Records not imported pending verification: 1", output.getvalue())
        self.assertFalse(
            Student.objects.filter(user__first_name="Suprith").exists()
        )

        azeem = Student.objects.get(admission_number="P1GH25S126015")
        yashawanth = Student.objects.get(admission_number="P18GH25S120645")
        self.assertTrue(azeem.registration_review_required)
        self.assertTrue(yashawanth.registration_review_required)
        self.assertEqual(azeem.source_serial_number, 3)
        self.assertEqual(azeem.semester.number, 3)
        self.assertFalse(azeem.user.has_usable_password())

        output = io.StringIO()
        call_command(
            "import_mca_students",
            semester=3,
            academic_year="2026-27",
            stdout=output,
        )
        self.assertEqual(
            Student.objects.filter(program=mca, semester__number=3).count(), 45
        )
        self.assertIn("duplicates skipped: 45", output.getvalue())

    def test_hod_dashboard_and_admin_are_limited_to_headed_departments(self):
        hod = User.objects.create_user(
            username="hod-scope",
            password="Password@123",
            role=User.Role.HOD,
            is_staff=True,
        )
        self.dept.hod = hod
        self.dept.save(update_fields=("hod",))

        other_department = Department.objects.create(
            name="Commerce", code="COMM"
        )
        other_program = Program.objects.create(
            department=other_department,
            name="BCom",
            code="BCOM",
        )
        other_semester = Semester.objects.create(
            program=other_program,
            number=1,
        )
        other_user = User.objects.create_user(
            username="outside-student",
            password="Password@123",
            role=User.Role.STUDENT,
            first_name="Outside",
            last_name="Student",
        )
        other_student = Student.objects.create(
            user=other_user,
            admission_number="COMM-001",
            department=other_department,
            program=other_program,
            academic_year=self.ay,
            semester=other_semester,
        )

        self.client.force_login(hod)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "HOD Dashboard")
        self.assertContains(dashboard, self.student.admission_number)
        self.assertNotContains(dashboard, other_student.admission_number)
        self.assertContains(dashboard, "Department students")

        student_admin_url = reverse(
            "admin:academics_student_change", args=[other_student.pk]
        )
        self.assertRedirects(
            self.client.get(student_admin_url),
            "/admin/",
            fetch_redirect_response=False,
        )
        academic_year_admin_url = reverse(
            "admin:academics_academicyear_change", args=[self.ay.pk]
        )
        self.assertEqual(self.client.get(academic_year_admin_url).status_code, 403)

        department_admin_url = reverse(
            "admin:academics_department_change", args=[self.dept.pk]
        )
        department_response = self.client.get(department_admin_url)
        self.assertEqual(department_response.status_code, 403)

        other_faculty_user = User.objects.create_user(
            username="outside-faculty",
            password="TestPassword@123",
            role=User.Role.FACULTY,
        )
        Faculty.objects.create(
            user=other_faculty_user,
            faculty_id="FAC-OUTSIDE",
            department=other_department,
        )
        unlinked_faculty_user = User.objects.create_user(
            username="unlinked-faculty",
            password="TestPassword@123",
            role=User.Role.FACULTY,
        )
        faculty_admin = admin.site._registry[Faculty]
        request = RequestFactory().get("/admin/academics/faculty/add/")
        request.user = hod
        faculty_user_field = faculty_admin.formfield_for_foreignkey(
            Faculty._meta.get_field("user"), request
        )
        self.assertFalse(
            faculty_user_field.queryset.filter(pk=other_faculty_user.pk).exists()
        )
        self.assertTrue(
            faculty_user_field.queryset.filter(pk=unlinked_faculty_user.pk).exists()
        )

    def test_mca_department_configuration_moves_only_verified_mca_records(self):
        mca_program = Program.objects.create(
            department=self.dept,
            name="Master of Computer Applications",
            code="MCA",
            duration_years=2,
        )
        mca_semester = Semester.objects.create(
            program=mca_program,
            number=3,
            name="Semester 3",
        )
        hod = User.objects.create_user(
            username="mca-hod",
            password="ExistingPassword@123",
            role=User.Role.HOD,
            is_staff=True,
            first_name="Rajeshwari",
            last_name="Ma'am",
        )
        self.dept.hod = hod
        self.dept.save(update_fields=("hod",))
        rajeshwari = Faculty.objects.create(
            user=hod,
            faculty_id="FAC-MCA-301EB",
            department=self.dept,
            designation="HOD",
        )
        assignment_data = (
            ("MCA301T", "Web Technologies", "FAC-MCA-301T", "Vijaya Lakshmi", ""),
            ("MCA302T", "Machine Learning", "FAC-MCA-302T", "Bharathi", ""),
            ("MCA303T", "Cloud Technologies", "FAC-MCA-303T", "Deeksha", ""),
            (
                "MCA301E(b)",
                "Data Analysis and Business Intelligence",
                "FAC-MCA-301EB",
                "Rajeshwari",
                "Ma'am",
            ),
        )
        mca_faculty = {rajeshwari.faculty_id: rajeshwari}
        for code, name, faculty_id, first_name, last_name in assignment_data:
            if faculty_id == rajeshwari.faculty_id:
                faculty = rajeshwari
            else:
                faculty_user = User.objects.create_user(
                    username=faculty_id.lower(),
                    password="ExistingPassword@123",
                    role=User.Role.FACULTY,
                    first_name=first_name,
                    last_name=last_name,
                )
                faculty = Faculty.objects.create(
                    user=faculty_user,
                    faculty_id=faculty_id,
                    department=self.dept,
                )
            mca_faculty[faculty_id] = faculty
            Subject.objects.create(
                code=code,
                name=name,
                semester=mca_semester,
                faculty=faculty,
            )
        mca_students = []
        for student_number in range(45):
            user = User.objects.create_user(
                username=f"mca-student-{student_number:03}",
                password="StudentPassword@123",
                role=User.Role.STUDENT,
            )
            mca_students.append(
                Student.objects.create(
                    user=user,
                    admission_number=f"2026-MCA-{student_number:03}",
                    department=self.dept,
                    program=mca_program,
                    academic_year=self.ay,
                    semester=mca_semester,
                )
            )

        call_command("configure_mca_department", stdout=io.StringIO())

        mca_department = Department.objects.get(code="MCA")
        self.dept.refresh_from_db()
        mca_program.refresh_from_db()
        self.assertEqual(mca_department.name, "Master of Computer Applications")
        self.assertEqual(
            mca_department.department_type,
            Department.DepartmentType.POSTGRADUATE,
        )
        self.assertEqual(
            mca_department.official_reference,
            "https://www.spmcollege.ac.in/mca/index",
        )
        self.assertEqual(mca_department.hod_id, hod.pk)
        self.assertIsNone(self.dept.hod_id)
        self.assertEqual(mca_program.department_id, mca_department.pk)
        self.assertEqual(
            Faculty.objects.filter(
                pk__in=[faculty.pk for faculty in mca_faculty.values()],
                department=mca_department,
            ).count(),
            4,
        )
        self.assertEqual(
            Student.objects.filter(
                program=mca_program,
                department=mca_department,
                academic_year=self.ay,
                semester=mca_semester,
            ).count(),
            45,
        )
        self.assertEqual(
            Student.objects.filter(program=self.prog, department=self.dept).count(),
            1,
        )
        self.assertEqual(
            list(
                Subject.objects.filter(semester=mca_semester)
                .order_by("code")
                .values_list("code", "faculty__faculty_id", "credits", "weekly_hours")
            ),
            [
                ("MCA301E(b)", "FAC-MCA-301EB", 4, 4),
                ("MCA301T", "FAC-MCA-301T", 4, 4),
                ("MCA302T", "FAC-MCA-302T", 4, 4),
                ("MCA303T", "FAC-MCA-303T", 4, 4),
            ],
        )
        audit_count = AuditLog.objects.filter(
            reason="Configure official MCA department and verified assignments."
        ).count()
        call_command("configure_mca_department", stdout=io.StringIO())
        self.assertEqual(
            AuditLog.objects.filter(
                reason="Configure official MCA department and verified assignments."
            ).count(),
            audit_count,
        )
        self.assertEqual(
            Student.objects.filter(
                pk__in=[student.pk for student in mca_students]
            ).values_list("user_id", "admission_number").count(),
            45,
        )

        outside_audit = AuditLog.objects.create(
            actor=self.admin,
            action=AuditLog.Action.UPDATE,
            object_id=str(self.student.pk),
            record_type="academics.student",
            record_repr="BCA outside department audit",
        )
        self.client.force_login(hod)
        dashboard = self.client.get(reverse("hod-dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Master of Computer Applications")
        self.assertContains(dashboard, "Postgraduate")
        self.assertContains(dashboard, "Rajeshwari")
        self.assertContains(dashboard, "45")
        for code, name, *_ in assignment_data:
            self.assertContains(dashboard, code)
            self.assertContains(dashboard, name)
        self.assertEqual(dashboard.context["hod_faculty"].count(), 4)
        self.assertGreaterEqual(
            dashboard.context["recent_activities"].count(), 8
        )
        self.assertNotIn(
            outside_audit.pk,
            [entry.pk for entry in dashboard.context["recent_activities"]],
        )
        audit_page = self.client.get(
            reverse("admin:academics_auditlog_changelist")
        )
        self.assertEqual(audit_page.status_code, 200)
        self.assertNotContains(audit_page, "BCA outside department audit")
        self.assertContains(audit_page, "Configure official MCA department")

        vijaya = mca_faculty["FAC-MCA-301T"].user
        self.client.force_login(vijaya)
        faculty_dashboard = self.client.get(reverse("faculty-dashboard"))
        self.assertEqual(faculty_dashboard.status_code, 200)
        self.assertContains(faculty_dashboard, "MCA301T")
        self.assertContains(faculty_dashboard, "Web Technologies")
        self.assertNotContains(faculty_dashboard, "Machine Learning")
        self.assertContains(faculty_dashboard, "45 assigned students")
        self.assertEqual(
            self.client.get(reverse("hod-dashboard")).status_code,
            403,
        )
        student_page = self.client.get(reverse("managed-students"))
        self.assertContains(student_page, "2026-MCA-000")
        self.assertNotContains(student_page, self.student.admission_number)

    def test_faculty_student_management_is_limited_to_assigned_semesters(self):
        other_semester = Semester.objects.create(
            program=self.prog, number=2, name="Semester 2"
        )
        other_faculty_user = User.objects.create_user(
            username="faculty-other-scope",
            password="Password@123",
            role=User.Role.FACULTY,
        )
        other_faculty = Faculty.objects.create(
            user=other_faculty_user,
            faculty_id="FAC-OTHER",
            department=self.dept,
        )
        Subject.objects.create(
            code="BCA202",
            name="Other semester subject",
            semester=other_semester,
            faculty=other_faculty,
        )
        other_student_user = User.objects.create_user(
            username="other-semester-student",
            password="Password@123",
            role=User.Role.STUDENT,
        )
        other_student = Student.objects.create(
            user=other_student_user,
            admission_number="2026-BCA-SEM2",
            department=self.dept,
            program=self.prog,
            academic_year=self.ay,
            semester=other_semester,
        )

        self.client.force_login(self.fac_user)
        list_response = self.client.get(reverse("managed-students"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.student.admission_number)
        self.assertNotContains(list_response, other_student.admission_number)
        self.assertEqual(
            self.client.get(
                reverse("managed-student-edit", args=[other_student.pk])
            ).status_code,
            404,
        )

    def test_faculty_can_create_a_student_in_assigned_semester_with_one_time_password(self):
        self.client.force_login(self.fac_user)
        response = self.client.post(reverse("managed-student-add"), {
            "admission_number": "2026-BCA-NEW",
            "first_name": "New",
            "last_name": "Student",
            "academic_year": self.ay.pk,
            "semester": self.sem.pk,
            "date_of_birth": "2005-11-23",
            "guardian_name": "Guardian",
            "guardian_phone": "",
            "address": "",
            "status": Student.Status.ACTIVE,
        })
        self.assertRedirects(
            response,
            reverse("managed-students"),
            fetch_redirect_response=False,
        )
        student = Student.objects.select_related("user").get(
            admission_number="2026-BCA-NEW"
        )
        self.assertEqual(student.user.username, student.admission_number)
        self.assertEqual(student.user.role, User.Role.STUDENT)
        self.assertTrue(student.user.must_change_password)
        self.assertTrue(student.user.has_usable_password())
        self.assertTrue(
            AuditLog.objects.filter(
                record_type="academics.student",
                object_id=str(student.pk),
                action=AuditLog.Action.CREATE,
                actor=self.fac_user,
            ).exists()
        )
        credentials_response = self.client.get(reverse("managed-students"))
        self.assertContains(credentials_response, "Temporary password:")
        self.assertNotContains(
            self.client.get(reverse("managed-students")),
            "Temporary password:",
        )

    def test_faculty_can_edit_assigned_student_without_changing_registration_or_account(self):
        self.client.force_login(self.fac_user)
        student_user_id = self.student.user_id
        response = self.client.post(
            reverse("managed-student-edit", args=[self.student.pk]),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "phone": "555-0101",
                "academic_year": self.ay.pk,
                "semester": self.sem.pk,
                "date_of_birth": "2005-11-23",
                "guardian_name": "Updated guardian",
                "guardian_phone": "",
                "address": "",
                "status": Student.Status.ACTIVE,
                "change_reason": "Corrected the student profile.",
            },
        )
        self.assertRedirects(
            response,
            reverse("managed-students"),
            fetch_redirect_response=False,
        )
        self.student.refresh_from_db()
        self.student.user.refresh_from_db()
        self.assertEqual(self.student.admission_number, "2026-BCA-001")
        self.assertEqual(self.student.user_id, student_user_id)
        self.assertEqual(self.student.user.get_full_name(), "Updated Name")
        self.assertEqual(self.student.user.phone, "555-0101")
        self.assertEqual(self.student.guardian_name, "Updated guardian")
        self.assertTrue(
            AuditLog.objects.filter(
                record_type="academics.student",
                object_id=str(self.student.pk),
                action=AuditLog.Action.UPDATE,
                actor=self.fac_user,
                reason="Corrected the student profile.",
            ).exists()
        )

    def test_hod_initial_password_is_hashed_one_time_and_must_be_changed(self):
        hod = User.objects.create_user(
            username="existing-hod",
            password="OldPassword@123",
            role=User.Role.HOD,
            is_staff=True,
        )
        self.dept.hod = hod
        self.dept.save(update_fields=("hod",))

        call_command(
            "provision_hod_account",
            initial_password="Initial@123",
            stdout=io.StringIO(),
        )
        hod.refresh_from_db()
        self.assertEqual(hod.username, "HOD")
        self.assertTrue(hod.check_password("Initial@123"))
        self.assertNotEqual(hod.password, "Initial@123")
        self.assertTrue(hod.must_change_password)
        self.assertTrue(hod.initial_password_provisioned)

        call_command(
            "provision_hod_account",
            initial_password="DoNotReset@123",
            stdout=io.StringIO(),
        )
        hod.refresh_from_db()
        self.assertTrue(hod.check_password("Initial@123"))
        self.assertTrue(hod.must_change_password)

        self.client.force_login(hod)
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertRedirects(dashboard_response, reverse("password-change"))
        change_response = self.client.post(reverse("password-change"), {
            "old_password": "Initial@123",
            "new_password1": "A-Long-New-Password@123",
            "new_password2": "A-Long-New-Password@123",
        })
        self.assertRedirects(change_response, reverse("dashboard"))
        hod.refresh_from_db()
        self.assertFalse(hod.must_change_password)
        self.assertTrue(hod.check_password("A-Long-New-Password@123"))
        call_command(
            "provision_hod_account",
            initial_password="DoNotReset@123",
            stdout=io.StringIO(),
        )
        hod.refresh_from_db()
        self.assertTrue(hod.check_password("A-Long-New-Password@123"))
        self.assertFalse(hod.must_change_password)
        self.assertEqual(hod.username, "HOD")
        self.assertTrue(hod.initial_password_provisioned)

    def test_desktop_api_requires_temporary_password_change(self):
        from rest_framework.authtoken.models import Token

        self.student_user.set_password("Temporary@123")
        self.student_user.must_change_password = True
        self.student_user.save(update_fields=("password", "must_change_password"))

        login_response = self.client.post(
            reverse("desktop-login"),
            {"username": self.student_user.username, "password": "Temporary@123"},
        )
        self.assertEqual(login_response.status_code, 403)
        self.assertFalse(Token.objects.filter(user=self.student_user).exists())

        token = Token.objects.create(user=self.student_user)
        summary_response = self.client.get(
            reverse("desktop-summary"),
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )
        self.assertEqual(summary_response.status_code, 403)

    def test_student_initial_passwords_are_audited_and_exported_once(self):
        from rest_framework.authtoken.models import Token

        self.student_user.set_unusable_password()
        self.student_user.save(update_fields=("password",))
        token = Token.objects.create(user=self.student_user)

        with tempfile.TemporaryDirectory() as directory:
            output_path = f"{directory}\\student-credentials.csv"
            call_command(
                "provision_student_initial_passwords",
                output_path=output_path,
                expected_count=1,
                stdout=io.StringIO(),
            )
            with open(output_path, encoding="utf-8", newline="") as credential_file:
                row = next(csv.DictReader(credential_file))

        self.student_user.refresh_from_db()
        self.assertEqual(row["registration_number"], self.student.admission_number)
        self.assertEqual(row["username"], self.student_user.username)
        self.assertTrue(self.student_user.check_password(row["temporary_password"]))
        self.assertTrue(self.student_user.must_change_password)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
        audit = AuditLog.objects.get(
            record_type="accounts.user",
            object_id=str(self.student_user.pk),
            reason="One-time initial student password provisioning.",
        )
        self.assertEqual(
            audit.changes["password"],
            {"old": "[redacted]", "new": "[redacted]"},
        )
        self.assertNotIn(row["temporary_password"], str(audit.changes))

    def test_hod_initial_password_can_be_generated_without_command_argument(self):
        hod = User.objects.create_user(
            username="generated-hod",
            password="OriginalPassword@123",
            role=User.Role.HOD,
            is_staff=True,
        )
        self.dept.hod = hod
        self.dept.save(update_fields=("hod",))
        output = io.StringIO()

        call_command(
            "provision_hod_account",
            generate_initial_password=True,
            stdout=output,
        )

        hod.refresh_from_db()
        password_line = next(
            line for line in output.getvalue().splitlines()
            if line.startswith("One-time initial HOD password: ")
        )
        password = password_line.split(": ", 1)[1]
        self.assertTrue(hod.check_password(password))
        self.assertTrue(hod.must_change_password)
        self.assertTrue(hod.initial_password_provisioned)
