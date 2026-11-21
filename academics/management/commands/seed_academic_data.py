from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from academics.models import Department, Program, AcademicYear, Semester, Student, Faculty
import datetime

User = get_user_model()

class Command(BaseCommand):
    help = "Seed realistic institutional sample data for Seshadripuram College Academic Management System"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Seshadripuram College institutional data...")

        # 1. Super Admin User
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Ramesh",
                "last_name": "Kumar",
                "email": "admin@spm.ac.in",
                "role": User.Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True
            }
        )
        if created:
            admin_user.set_password("Admin@123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Super Admin: admin / Admin@123"))

        # 2. Academic Year
        ay, _ = AcademicYear.objects.get_or_create(
            name="2026-27",
            defaults={
                "start_date": datetime.date(2026, 6, 1),
                "end_date": datetime.date(2027, 5, 31),
                "is_current": True
            }
        )

        # 3. Departments
        dept_data = [
            ("Commerce & Management", "COMM", "Undergraduate & postgraduate business and commerce education"),
            ("Computer Science & Applications", "CS", "Computer applications, software systems, and data analytics"),
            ("Arts & Humanities", "ARTS", "Language, journalism, and social sciences"),
            ("Science", "SCI", "Physics, chemistry, and mathematics programs")
        ]
        depts = {}
        for name, code, desc in dept_data:
            d, _ = Department.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc, "is_active": True}
            )
            depts[code] = d

        # 4. Programs & Semesters
        prog_data = [
            ("COMM", "Bachelor of Commerce", "BCOM", 3),
            ("COMM", "Bachelor of Business Administration", "BBA", 3),
            ("CS", "Bachelor of Computer Applications", "BCA", 3),
            ("CS", "Master of Computer Applications", "MCA", 2)
        ]
        programs = {}
        for d_code, p_name, p_code, dur in prog_data:
            prog, _ = Program.objects.get_or_create(
                code=p_code,
                defaults={"department": depts[d_code], "name": p_name, "duration_years": dur, "is_active": True}
            )
            programs[p_code] = prog
            for sem_num in range(1, dur * 2 + 1):
                Semester.objects.get_or_create(
                    program=prog,
                    number=sem_num,
                    defaults={"name": f"Semester {sem_num}"}
                )

        # 5. Faculty Profiles
        faculty_info = [
            ("faculty_cs1", "Priya", "Natarajan", "CS", "Associate Professor - Data Science"),
            ("faculty_comm1", "Anand", "Venkatesh", "COMM", "Professor - Financial Accounting"),
            ("faculty_cs2", "Suresh", "Babu", "CS", "Assistant Professor - Cloud Computing")
        ]
        for username, fname, lname, dcode, desig in faculty_info:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fname, "last_name": lname,
                    "email": f"{username}@spm.ac.in", "role": User.Role.FACULTY
                }
            )
            if created:
                u.set_password("Faculty@123")
                u.save()
            Faculty.objects.get_or_create(
                user=u,
                defaults={
                    "faculty_id": f"FAC-{dcode}-{u.id:03d}",
                    "department": depts[dcode],
                    "designation": desig,
                    "is_active": True
                }
            )

        # 6. Student Profiles
        student_info = [
            ("std_aarav", "Aarav", "Sharma", "CS", "BCA", 3, "2024-BCA-001"),
            ("std_diya", "Diya", "Reddy", "COMM", "BCOM", 1, "2026-BCM-014"),
            ("std_rohan", "Rohan", "Mehta", "COMM", "BBA", 5, "2024-BBA-082"),
            ("std_ananya", "Ananya", "Iyer", "CS", "BCA", 1, "2026-BCA-005"),
            ("std_karan", "Karan", "Patel", "CS", "MCA", 1, "2026-MCA-021")
        ]
        for username, fname, lname, dcode, pcode, sem_num, adm_no in student_info:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fname, "last_name": lname,
                    "email": f"{username}@student.spm.ac.in", "role": User.Role.STUDENT
                }
            )
            if created:
                u.set_password("Student@123")
                u.save()
            sem = Semester.objects.get(program=programs[pcode], number=sem_num)
            Student.objects.get_or_create(
                admission_number=adm_no,
                defaults={
                    "user": u,
                    "department": depts[dcode],
                    "program": programs[pcode],
                    "academic_year": ay,
                    "semester": sem,
                    "status": Student.Status.ACTIVE
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database: {Department.objects.count()} Departments, "
            f"{Program.objects.count()} Programs, {Faculty.objects.count()} Faculty, "
            f"{Student.objects.count()} Students."
        ))
