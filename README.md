# Seshadripuram College – Smart Academic Management System

Python dual-platform academic management system:
- Web: Django + Django REST Framework
- Desktop: PySide6 client
- Database: PostgreSQL (SQLite is supported for initial local setup)

Both clients communicate with the same Django API.

## Phase 1 setup (Windows PowerShell)

1. Install Python 3.11+ and PostgreSQL 15+ (PostgreSQL is optional for the first smoke test).
2. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values.
4. Run migrations and create an administrator:

```powershell
python manage.py makemigrations accounts academics
python manage.py migrate
python manage.py seed_mca_subjects
python manage.py import_mca_students --semester 3 --academic-year 2026-27
python manage.py createsuperuser
python manage.py import_official_faculty_directory
python manage.py runserver
```

5. Open:
- Admin: http://127.0.0.1:8000/admin/
- API health: http://127.0.0.1:8000/api/health/

6. Start the desktop client in another terminal:

```powershell
python desktop/main.py
```

`seed_mca_subjects` creates or updates the four MCA Semester III subjects and their
faculty/HOD profiles. New faculty accounts have no password until an administrator sets
one; the command does not invent contact details.
After the MCA program, its four verified faculty assignments, and 45 Semester III
students are present, run `python manage.py configure_mca_department` to place them in
the distinct postgraduate MCA department. The command checks the expected records,
keeps student and subject identifiers and academic details intact, transfers the
existing Rajeshwari HOD assignment from CS to MCA, and records the department changes
in the audit history. It stops rather than reassigning records if its preconditions do
not match.
`import_mca_students` imports the 45 complete student registrations after the semester
and academic year have been confirmed. Suprith is omitted until the registration number
is verified; suspicious source values are preserved and flagged rather than corrected.

## Official faculty directory

The public directory is available at `/faculty/`; individual profiles are available at
`/faculty/<id>/`. Authorized administrators can manage directory profiles in Django
admin. The idempotent `import_official_faculty_directory` command imports the verified
names, designations, and qualifications from the college's
[PG Commerce teaching-faculty directory](https://www.spmcollege.ac.in/mcom/teaching-faculty).
It links the Principal profile to the existing Super Admin account when one exists,
updating the Principal's profile fields without changing the account username or
password. It does not create login accounts or invent contact details, biographies, or
faculty-to-MCA-subject assignments. Public directory profiles are separate from
faculty login accounts.

## Administrative access and audit history

The Django admin is the shared record-management workspace. Super Admin accounts are
Django superusers and can manage all registered admin modules, users, and permissions.
HODs can manage academic records and faculty/student accounts but cannot view or modify
Super Admin accounts. Faculty access remains limited to assigned subjects and their
students; students have read-only access to their own academic information.

Changes made through Django admin and subject-edit pages are recorded in the
read-only **Audit history** module, including the actor, timestamp, record, changed
values, and optional reason. Password changes are recorded without storing password
values. Subjects can be archived with their active status instead of being deleted.

Role dashboards are available at `/`, `/hod/dashboard/`, `/faculty/dashboard/`, and
`/student/dashboard/`. HOD access
is limited to headed departments, faculty access is limited to assigned subjects and
their related student semesters, and students can view only their own academic data.
HOD-created accounts, student accounts created through student management, and accounts
whose password is reset in Django admin must change that password at first sign-in.
The desktop API also denies access until that required change is completed through web
sign-in.
Existing student accounts imported without usable passwords still require an
administrator-managed password reset before those students can sign in.

The existing HOD account can be provisioned once after migrations with
`python manage.py provision_hod_account`. The command prompts for the initial password
without echoing it. Provisioning preserves the existing HOD and faculty relationship,
requires a password change at first sign-in, and will not reset the password on
subsequent runs.

For the currently imported 45 students, `python manage.py
provision_student_initial_passwords --output-path <private-csv-path>` generates
individual temporary passwords, revokes existing desktop tokens, requires a password
change at first sign-in, and records redacted audit events. It refuses to overwrite an
existing export, change accounts with usable passwords, or proceed if the student count
differs from 45. Keep the CSV private, distribute each credential securely, and delete
the export after distribution.

Attendance, examination/results, timetable, and analytical report modules do not exist
in this project yet; their records and workflows are not created by this update.

Set `API_BASE_URL` in `.env` if the API is hosted elsewhere.

## PostgreSQL configuration

Create a database and user, then set `DB_ENGINE=postgres` and configure `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env`.

For the initial smoke test, leave `DB_ENGINE=sqlite`.

## Phase 1 scope

Included:
- Django project and REST API foundation
- Custom user model with role field
- Initial department, program, academic year, semester, student and faculty models
- Django admin registration
- API health endpoint
- PySide6 desktop shell that checks backend connectivity

Not yet implemented:
- Production login flows and JWT token lifecycle
- Student/faculty CRUD screens
- Attendance and examination workflows

## Important

Use fictional demo data until the college authorizes access to real student and staff records.
Change `SECRET_KEY`, database credentials, allowed hosts, CORS and deployment settings before production.
