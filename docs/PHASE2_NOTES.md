# Phase 2 implementation notes

## Authentication
- Web: Django session authentication, CSRF-protected login and logout.
- Desktop: username/password exchanged over the local HTTPS-ready API boundary for a DRF token.
- Role is displayed in the interface. The current dashboard aggregates data for institutional staff roles and restricts student summary to the signed-in student's own linked profile.

## Next hardening tasks
- Enforce object-level department and HOD scoping on every CRUD/API endpoint.
- Add password reset, account lifecycle and audit logging.
- Add HTTPS and secure token storage before any non-local deployment.
- Replace Django Admin links with purpose-built CRUD screens.
