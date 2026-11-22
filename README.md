# Seshadripuram College — Smart Academic Management System

A dual-platform academic management system built with **Python, Django REST Framework and PySide6**.

The application provides a shared backend for web and desktop clients, with a common database and centralized academic records.

## 1. Project Architecture

| Component | Technology |
|---|---|
| Backend | Python, Django |
| REST API | Django REST Framework |
| Web application | Django |
| Desktop application | PySide6 |
| Primary database | PostgreSQL 15+ |
| Initial local database | SQLite |
| Authentication | Django authentication and API authentication |
| Environment configuration | `.env` |

Both clients communicate with the same Django backend and API.

```text
                 SMART ACADEMIC MANAGEMENT SYSTEM
                               |
                     Django Backend + API
                               |
                 ---------------------------
                 |                         |
          Web Application             Desktop Client
              Django                     PySide6
                 |                         |
                 -------- REST API --------
                               |
                        Database Layer
                               |
                    PostgreSQL / SQLite
                               |
          -----------------------------------------
          |                |                      |
       Students          Faculty              Academic Data
```

## 2. Phase 1 — Windows Setup

### Prerequisites

- Python 3.11 or newer
- Git
- Visual Studio Code or another Python IDE
- PostgreSQL 15 or newer (optional for the initial SQLite smoke test)

### Step 1: Open the project directory

Open PowerShell and navigate to the existing project directory:

```powershell
cd C:\Project\seshadripuram_academic_system_phase2\seshadripuram_academic_system
```

### Step 2: Create and activate the virtual environment

```powershell
py -3.11 -m venv .venv

.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt
```

### Step 3: Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with the required settings.

Do not commit `.env` to GitHub.

### Step 4: Verify Django configuration

```powershell
python manage.py check
```

Inspect existing migrations:

```powershell
python manage.py showmigrations
```

**Important:** Do not automatically generate or apply migrations until the existing database schema and migration history have been inspected. Back up the database before applying any migration changes.

### Step 5: Apply verified migrations

After confirming that the migration history and database schema are consistent:

```powershell
python manage.py migrate
```

### Step 6: Configure academic data

Run the following commands only after confirming that the corresponding management commands exist and their prerequisites are satisfied:

```powershell
python manage.py seed_mca_subjects

python manage.py import_mca_students --semester 3 --academic-year 2026-27

python manage.py configure_mca_department
```

The MCA department configuration command should run after the MCA program, verified faculty assignments and 45 Semester III student records are available.

It checks the expected records, preserves student and subject identifiers and academic details, transfers the existing Rajeshwari HOD assignment from CS to MCA, and records department changes in the audit history.

It must stop if its preconditions do not match.

### Step 7: Configure administrator and faculty directory

Create a Super Admin account if one does not already exist:

```powershell
python manage.py createsuperuser
```

Import the verified public faculty directory:

```powershell
python manage.py import_official_faculty_directory
```

The faculty directory import must not create login accounts or invent contact details.

### Step 8: Start the Django server

```powershell
python manage.py runserver
```

Open:

- Django Admin: http://127.0.0.1:8000/admin/
- API Health: http://127.0.0.1:8000/api/health/

### Step 9: Start the desktop client

Open a second PowerShell terminal, activate the same virtual environment and run:

```powershell
python desktop/main.py
```

Set `API_BASE_URL` in `.env` if the backend is hosted at another address.

---

## 3. Academic Data Configuration

### MCA Semester III

The project is configured for the MCA program, academic year 2026–27 and Semester III.

The four verified subject assignments are:

| Subject Code | Subject Name | Faculty |
|---|---|---|
| MCA301T | Web Technologies | Vijaya Lakshmi |
| MCA302T | Machine Learning | Bharathi |
| MCA303T | Cloud Technologies | Deeksha |
| MCA301E(b) | Data Analysis and Business Intelligence | Rajeshwari Ma'am (HOD) |

The academic configuration includes:

- MCA department
- MCA program
- Semester III
- Academic year 2026–27
- Four verified subject assignments
- 45 existing MCA student registrations

### Student import

The command:

```powershell
python manage.py import_mca_students --semester 3 --academic-year 2026-27
```

imports the 45 complete student registrations after the semester and academic year have been confirmed.

Important data rules:

- Preserve the original registration numbers.
- Preserve student names as supplied.
- Do not invent missing registration numbers.
- Suprith remains omitted until the registration number is verified.
- Suspicious source values must be preserved and flagged rather than silently corrected.
- Do not duplicate existing student profiles.

### Subject seeding

The command:

```powershell
python manage.py seed_mca_subjects
```

creates or updates the four MCA Semester III subjects and their verified faculty/HOD profile relationships.

It must not invent faculty contact information or create unverified faculty assignments.

---

## 4. Official Faculty Directory

The public faculty directory is available at:

- Faculty directory: `/faculty/`
- Individual faculty profiles: `/faculty/<id>/`

The verified source directory is:

[PG Commerce Teaching Faculty Directory](https://www.spmcollege.ac.in/mcom/teaching-faculty)

The idempotent command:

```powershell
python manage.py import_official_faculty_directory
```

imports verified:

- Faculty names
- Designations
- Qualifications

It links the Principal profile to the existing Super Admin account when one exists, updating the Principal's profile fields without changing the account username or password.

Important:

- Public directory profiles are separate from faculty login accounts.
- The import does not create login accounts.
- It does not invent contact details or biographies.
- It does not create faculty-to-MCA-subject assignments.
- Do not treat the PG Commerce directory as an authoritative MCA teaching assignment list.

---

## 5. User Roles and Access Control

The application supports four main roles.

| Role | Access |
|---|---|
| Super Admin | System-wide administration |
| HOD | Department-level academic administration |
| Faculty | Assigned subjects and authorized students |
| Student | Own academic information |

### Super Admin

- Manage registered admin modules.
- Manage users and permissions.
- Manage academic records.
- View system-wide records.
- Review audit history.

Super Admin accounts are Django superusers.

### HOD

- Manage authorized academic records.
- Manage faculty and student accounts within headed departments.
- View department-level academic information.
- Cannot view or modify Super Admin accounts.

### Faculty

- View assigned subjects.
- View authorized students.
- Access records within assigned subjects and semesters.
- Cannot access unrelated departments or other faculty members' private information.

### Student

- Read-only access to their own academic information.
- Cannot view other students' private records.
- Can edit only their own first name, last name and phone number through `/student/profile/`.
- Cannot edit their registration number or academic records.

### Dashboard routes

| Role | Route |
|---|---|
| Super Admin | `/` |
| HOD | `/hod/dashboard/` |
| Faculty | `/faculty/dashboard/` |
| Student | `/student/dashboard/` |

All permissions must be enforced on the server through Django views, API permissions, querysets and object-level authorization. Hiding links in the frontend is not sufficient.

---

## 6. Administrative Access and Audit History

Django Admin is the shared record-management workspace.

Authorized administrators can manage registered modules, users, academic records and permissions.

### Audit history

Changes made through Django Admin and subject-edit pages are recorded in the read-only Audit History module.

Audit records include:

- Actor
- Timestamp
- Record
- Changed values
- Optional reason

Password changes are recorded without storing password values.

### Subject management

Subjects can be archived using their active status instead of being permanently deleted.

This preserves historical academic relationships.

---

## 7. Account Provisioning and Password Management

### HOD account

The existing HOD account can be provisioned using:

```powershell
python manage.py provision_hod_account
```

The command:

- Prompts for the initial password without echoing it.
- Preserves the existing HOD and faculty relationship.
- Requires a password change at first sign-in.
- Does not reset the password on subsequent runs.

### Student accounts

For the 45 imported students:

```powershell
python manage.py provision_student_initial_passwords --output-path <private-csv-path>
```

The command:

- Generates individual temporary passwords.
- Revokes existing desktop tokens.
- Requires password change at first sign-in.
- Records redacted audit events.
- Refuses to overwrite an existing export.
- Refuses to change accounts with usable passwords.
- Stops if the student count differs from 45.

Keep the generated CSV private, distribute credentials securely and delete the export after distribution.

### Password security

- Use Django's `set_password()` for password updates.
- Never store plaintext passwords in the database.
- Never print passwords in application logs.
- Require first-login password changes where configured.
- Do not reset passwords automatically when the server starts.
- Revoke affected API tokens after credential resets.
- Restrict account management to authorized administrators.

Existing imported student accounts without usable passwords require an administrator-managed password reset before students can sign in.

The desktop API must deny access until a required password change is completed through web sign-in.

---

## 8. Database Configuration

The application supports PostgreSQL and SQLite.

### PostgreSQL configuration

PostgreSQL is the recommended database for production and shared deployments.

Install PostgreSQL 15 or newer, create a database and user, and configure `.env`:

```env
DB_ENGINE=postgres
DB_NAME=academic_management
DB_USER=academic_user
DB_PASSWORD=your_secure_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Use a strong database password and do not commit it to GitHub.

### SQLite configuration

SQLite is supported for initial local development and smoke testing.

Set:

```env
DB_ENGINE=sqlite
```

The default SQLite database file is:

```text
db.sqlite3.recovered-working.sqlite3
```

To select another database file:

```env
DB_SQLITE_PATH=db.sqlite3.recovered-working.sqlite3
```

Relative paths are resolved from the Django project directory.

### Database recovery precautions

The recovered working database is a historical snapshot, not proof that all recent records have been recovered.

- Keep the malformed original database untouched.
- Keep isolated recovery copies untouched.
- Preserve the valid Git snapshot.
- Reconcile newer records before treating the recovered database as authoritative.
- Back up the verified working database before migrations or data changes.
- Never recreate an empty database simply to bypass an error.

The SQLite header `SQLite format 3` is normal for a SQLite database file. Database validity must be determined through integrity checks and schema inspection.

---

## 9. Phase 1 — Current Scope

### Included in the Phase 1 foundation

- Django project foundation
- Django REST Framework API foundation
- Custom user model with role field
- Initial department model
- Program model
- Academic year model
- Semester model
- Student model
- Faculty model
- Django Admin registration
- API health endpoint
- PySide6 desktop shell
- Desktop backend connectivity check

### Not yet implemented or requiring completion and verification

- Production-ready web login and session lifecycle
- Production-ready API authentication and JWT token lifecycle
- Complete student CRUD screens
- Complete faculty CRUD screens
- Attendance management
- Examination and results management
- Timetable management
- Analytical reporting modules

Do not represent planned modules as completed features. Verify the actual implementation and tests before updating this status.

---

## 10. Security and Production Preparation

Before production deployment:

1. Replace the development `SECRET_KEY`.
2. Configure secure database credentials.
3. Configure `ALLOWED_HOSTS`.
4. Configure CORS for trusted origins only.
5. Enable appropriate HTTPS and secure cookie settings.
6. Disable Django debug mode.
7. Restrict database access.
8. Protect API authentication and token lifecycle.
9. Verify server-side role permissions.
10. Back up the database regularly.
11. Protect credential exports.
12. Use fictional demo data until the college authorizes access to real student and staff records.

---

## 11. Development and Recovery Principles

This is an existing project, not a new application.

All future development must:

- Preserve existing project structure.
- Preserve existing student and faculty records.
- Preserve existing account relationships.
- Preserve verified MCA subject assignments.
- Preserve the current UI and working functionality.
- Avoid unnecessary database migrations.
- Avoid duplicate user and student records.
- Use reversible, documented database changes.
- Test changes before declaring them complete.

**The web application and desktop client must use the same Django backend and authorized data source.**
