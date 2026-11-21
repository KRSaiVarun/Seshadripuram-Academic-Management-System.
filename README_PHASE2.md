# Phase 2 — Glassmorphism dashboards and role-aware sign-in

This update adds a responsive Django web dashboard and a matching PySide6 desktop client.
Both clients use the same Django backend and database.

## What is included
- Django session login/logout for the web interface.
- Authenticated dashboard with role-aware aggregate counts.
- A unified academic workspace: the dashboard and Django CRUD pages share college branding and module navigation.
- Dark glassmorphism UI, responsive layout, animated metric counters, floating ambient gradients and hover transitions.
- PySide6 sign-in using a Django REST token endpoint.
- Desktop overview that retrieves live counts from the same backend.
- Token-authenticated desktop summary endpoint.

## Setup (Windows PowerShell)
1. Extract the Phase 2 ZIP.
2. Open PowerShell in `seshadripuram_academic_system`.
3. Create and activate a virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Create `.env` from `.env.example` (SQLite is the default for local development).
6. Create database tables and an administrator:
   ```powershell
   python manage.py makemigrations accounts academics
   python manage.py migrate
   python manage.py createsuperuser
   ```
7. Start the web backend:
   ```powershell
   python manage.py runserver
   ```
8. Open `http://127.0.0.1:8000/` and sign in with the superuser credentials.
9. In a second PowerShell window, activate the same environment and run:
   ```powershell
   python desktop/main.py
   ```
   Sign in using the same Django account.

## MCA Semester III subjects and access

After applying migrations, populate or update the four MCA Semester III subjects and their
faculty assignments with:

```powershell
python manage.py seed_mca_subjects
```

The command is safe to rerun. Newly created faculty accounts have no password set; a
superuser must set initial passwords before those faculty members can sign in. Email and
phone fields are left blank unless an administrator supplies verified contact details.
The HOD can manage academic records and faculty/student accounts in the admin workspace.
Faculty can see their assigned subjects and edit those subjects, but cannot reassign or
delete them. Students see subjects for their current semester.

Import the supplied 45 complete MCA student records after reviewing the placement:

```powershell
python manage.py import_mca_students --semester 3 --academic-year 2026-27
```

The importer is safe to rerun, preserves the supplied registration numbers and source
serial numbers, creates accounts with unusable passwords, and reports Suprith's
unverified registration separately. Azeem Ullah Khan's and Yashawanth K M's registration
numbers are preserved as supplied and flagged for administrator review. Student admins
can search, filter, sort, paginate, view and edit records, and export selected records to
CSV. Faculty can only view students in semesters where they have an assigned subject.

## Admin roles and audit history

Super Admin accounts are Django superusers with access to every registered admin
module. HODs can manage academic records and faculty/student accounts, but cannot view,
change, or delete Super Admin accounts. Faculty remain restricted to assigned subjects
and students in their teaching semesters. The existing admin forms support editing
records; subject records can be archived without removing them.

The read-only **Audit history** admin module records creates, edits, and deletes made
through Django admin, including the actor, timestamp, record, field changes, and
optional correction reason. Subject edits through the faculty dashboard are also
audited. Password reset events are logged without storing password values.

## Important
- The desktop app uses token authentication. Tokens are created at first successful desktop login.
- The dashboard's student, faculty, department and other academic-module links open Django's record-management pages within the same branded workspace and return navigation.
- Attendance, examination/marks/results workflows, timetable, notifications, and detailed analytics are not implemented in this phase. There are no corresponding models or management pages yet.
- Demo visual references are not real college records. Add only verified, authorized college data.
- Before deployment: set a strong `SECRET_KEY`, `DEBUG=False`, configure `ALLOWED_HOSTS`, HTTPS, backups, and institution-approved access controls.
