"""
Per-role access map for the console. Every existing staff/superuser
account keeps seeing everything — restriction only ever applies to a
user explicitly given a StaffProfile with a role other than the default
'full_access' (see accounts.models.StaffProfile).

Adding a new restricted role later is just a new key in ROLE_PERMISSIONS
plus a `staff_profile.role` choice — no new plumbing required, since every
generic-CRUD check and dedicated-view check below already reads from here.

Two independent namespaces per role:
- 'manage' / 'view' — registry slugs (admin_console/registry.py), for the
  generic add/edit/delete CRUD scaffold.
- 'dedicated_manage' / 'dedicated_view' — names for the hand-built views
  (Applications, Students, Invoices, Payments, ...) that aren't in the
  registry because they carry real business logic beyond a plain form.
"""

FULL_ACCESS = 'full_access'

ROLE_PERMISSIONS = {
    'exam_officer': {
        'manage': {'results', 'attendance-records'},
        'view': {'course-registrations', 'courses'},
        'dedicated_view': {'students'},
        'dedicated_manage': {'gradesheets'},
    },
    'registrar': {
        # Admissions + academic structure/records — not finance.
        'manage': {
            'admission-cycles', 'academic-sessions', 'courses', 'course-registrations',
            'timetable', 'programmes', 'departments', 'student-announcements',
        },
        'view': {'results', 'attendance-records'},
        'dedicated_view': set(),
        'dedicated_manage': {'applications', 'students'},
    },
    'bursar': {
        # Finance only — sets fee amounts, monitors/reconciles what's been paid.
        'manage': {'fee-structures', 'fee-structure-items'},
        'view': set(),
        'dedicated_view': {'students', 'invoices', 'payments', 'student-invoices', 'student-payments'},
        'dedicated_manage': set(),
    },
    'academic_secretary': {
        # Day-to-day academic administration — scheduling/coordination
        # (Timetable, Assignments, Announcements, Courses) plus a share of
        # Registrar's academic-records territory (Sessions, Programmes,
        # Departments). Not admissions or student-record edits — that stays
        # Registrar's own dedicated_manage.
        'manage': {
            'timetable', 'assignments', 'student-announcements', 'courses',
            'academic-sessions', 'programmes', 'departments',
        },
        'view': {'course-registrations', 'results', 'attendance-records'},
        'dedicated_view': {'students'},
        'dedicated_manage': set(),
    },
}


def get_role(user):
    if user.is_superuser:
        return FULL_ACCESS
    profile = getattr(user, 'staff_profile', None)
    return profile.role if profile else FULL_ACCESS


def is_full_access(user):
    return get_role(user) == FULL_ACCESS


def can_view(user, slug):
    role = get_role(user)
    if role == FULL_ACCESS:
        return True
    perms = ROLE_PERMISSIONS.get(role, {})
    return slug in perms.get('manage', ()) or slug in perms.get('view', ())


def can_manage(user, slug):
    role = get_role(user)
    if role == FULL_ACCESS:
        return True
    return slug in ROLE_PERMISSIONS.get(role, {}).get('manage', ())


def can_view_dedicated(user, name):
    role = get_role(user)
    if role == FULL_ACCESS:
        return True
    perms = ROLE_PERMISSIONS.get(role, {})
    return name in perms.get('dedicated_view', ()) or name in perms.get('dedicated_manage', ())


def can_manage_dedicated(user, name):
    role = get_role(user)
    if role == FULL_ACCESS:
        return True
    return name in ROLE_PERMISSIONS.get(role, {}).get('dedicated_manage', ())


def visible_slugs(user):
    """Registry slugs this user may at least view. None means "everything"
    (full access) — callers must check that sentinel before treating the
    result as a restricting set."""
    role = get_role(user)
    if role == FULL_ACCESS:
        return None
    perms = ROLE_PERMISSIONS.get(role, {})
    return perms.get('manage', set()) | perms.get('view', set())


def visible_dedicated(user):
    """Dedicated-view names this user may at least view. None means
    "everything" (full access)."""
    role = get_role(user)
    if role == FULL_ACCESS:
        return None
    perms = ROLE_PERMISSIONS.get(role, {})
    return perms.get('dedicated_view', set()) | perms.get('dedicated_manage', set())
