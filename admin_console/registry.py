"""
Declarative registry driving the generic CRUD scaffold — one entry per
model that's safe for a plain ModelForm (no side effects beyond a normal
save). AdmissionCycle is included here (its save() override that enforces
"only one active cycle" still fires normally through a ModelForm). The
models with real business logic — Application (status/log), ApplicationInvoice
/ApplicationPayment (frozen financial records), SiteSettings/AboutContent
(singletons), and User accounts — are deliberately NOT here; see
admin_console/views.py's dedicated handlers for those instead.

`list_fields` supports dotted lookups and properties (resolved via
`admin_console.utils.resolve_value`), not just plain model fields.
"""

from dataclasses import dataclass, field


@dataclass
class ManagedModel:
    slug: str
    model: type
    label: str
    singular: str
    icon: str
    category: str
    list_fields: list          # [(attr_path, column_label), ...]
    search_fields: list = field(default_factory=list)    # ORM __icontains lookups
    filter_fields: list = field(default_factory=list)     # [(field_name, label), ...] — choices pulled from the model
    form_fields: list = field(default_factory=list)       # passed to modelform_factory
    can_delete: bool = True
    ordering: str | None = None


def _build_registry():
    from accounts.models import StaffProfile
    from admissions.models import AdmissionCycle
    from students.models import (
        AcademicSession, Announcement, Assignment, AttendanceRecord, Course, CourseRegistration,
        FeeStructure, FeeStructureItem, Result, TimetableEntry,
    )
    from website.models import (
        ContactMessage, CoreValue, Department, Event, Facility, GalleryCategory, GalleryImage,
        NewsArticle, Programme, Statistic, StudentLifeActivity, WhyChooseItem,
    )

    entries = [
        ManagedModel(
            slug='admission-cycles', model=AdmissionCycle, label='Admission Cycles', singular='Admission Cycle',
            icon='fa-solid fa-calendar-check', category='Admissions',
            list_fields=[('session', 'Session'), ('is_active', 'Active'), ('fee', 'Fee'),
                         ('opens_at', 'Opens'), ('closes_at', 'Closes')],
            search_fields=['session'],
            filter_fields=[('is_active', 'Active')],
            form_fields=['session', 'is_active', 'fee', 'opens_at', 'closes_at'],
        ),
        ManagedModel(
            slug='programmes', model=Programme, label='Programmes', singular='Programme',
            icon='fa-solid fa-graduation-cap', category='Academics',
            list_fields=[('code', 'Code'), ('name', 'Name'), ('category', 'Category'),
                         ('department', 'Department'), ('is_featured', 'Featured'), ('is_active', 'Active')],
            search_fields=['name', 'code'],
            filter_fields=[('category', 'Category'), ('department', 'Department'), ('is_active', 'Active')],
            form_fields=['name', 'code', 'category', 'department', 'duration', 'image', 'description',
                         'requirement', 'careers', 'is_featured', 'is_active', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='departments', model=Department, label='Departments', singular='Department',
            icon='fa-solid fa-building-columns', category='Academics',
            list_fields=[('name', 'Name'), ('head_name', 'Head'), ('is_active', 'Active'), ('order', 'Order')],
            search_fields=['name', 'head_name'],
            filter_fields=[('is_active', 'Active')],
            form_fields=['name', 'head_name', 'icon', 'description', 'order', 'is_active'],
            ordering='order',
        ),
        ManagedModel(
            slug='facilities', model=Facility, label='Facilities', singular='Facility',
            icon='fa-solid fa-hospital', category='Academics',
            list_fields=[('name', 'Name'), ('order', 'Order'), ('is_active', 'Active')],
            search_fields=['name'],
            filter_fields=[('is_active', 'Active')],
            form_fields=['name', 'description', 'image', 'order', 'is_active'],
            ordering='order',
        ),
        ManagedModel(
            slug='student-life', model=StudentLifeActivity, label='Student Life Activities', singular='Activity',
            icon='fa-solid fa-people-group', category='Academics',
            list_fields=[('title', 'Title'), ('order', 'Order'), ('is_active', 'Active')],
            search_fields=['title'],
            filter_fields=[('is_active', 'Active')],
            form_fields=['icon', 'title', 'description', 'order', 'is_active'],
            ordering='order',
        ),
        ManagedModel(
            slug='statistics', model=Statistic, label='Homepage Statistics', singular='Statistic',
            icon='fa-solid fa-chart-simple', category='Website',
            list_fields=[('label', 'Label'), ('value', 'Value'), ('suffix', 'Suffix'), ('order', 'Order')],
            search_fields=['label'],
            form_fields=['label', 'value', 'suffix', 'icon', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='why-choose', model=WhyChooseItem, label='Why Choose Us Cards', singular='Card',
            icon='fa-solid fa-star', category='Website',
            list_fields=[('title', 'Title'), ('order', 'Order'), ('is_active', 'Active')],
            search_fields=['title'],
            filter_fields=[('is_active', 'Active')],
            form_fields=['icon', 'title', 'description', 'order', 'is_active'],
            ordering='order',
        ),
        ManagedModel(
            slug='core-values', model=CoreValue, label='Core Values', singular='Core Value',
            icon='fa-solid fa-heart', category='Website',
            list_fields=[('title', 'Title'), ('order', 'Order')],
            search_fields=['title'],
            form_fields=['icon', 'title', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='news', model=NewsArticle, label='News Articles', singular='Article',
            icon='fa-solid fa-newspaper', category='Website',
            list_fields=[('title', 'Title'), ('category', 'Category'), ('date', 'Date'),
                         ('status', 'Status'), ('is_featured', 'Featured')],
            search_fields=['title', 'excerpt', 'author'],
            filter_fields=[('status', 'Status'), ('category', 'Category')],
            form_fields=['title', 'category', 'author', 'date', 'image', 'excerpt', 'content',
                         'is_featured', 'status'],
        ),
        ManagedModel(
            slug='events', model=Event, label='Events', singular='Event',
            icon='fa-solid fa-calendar-star', category='Website',
            list_fields=[('title', 'Title'), ('category', 'Category'), ('date', 'Date'), ('is_active', 'Active')],
            search_fields=['title', 'description'],
            filter_fields=[('category', 'Category'), ('is_active', 'Active')],
            form_fields=['title', 'date', 'location', 'category', 'description', 'is_active'],
        ),
        ManagedModel(
            slug='gallery-categories', model=GalleryCategory, label='Gallery Categories', singular='Category',
            icon='fa-solid fa-folder-tree', category='Website',
            list_fields=[('name', 'Name'), ('order', 'Order')],
            search_fields=['name'],
            form_fields=['name', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='gallery-images', model=GalleryImage, label='Gallery Images', singular='Image',
            icon='fa-solid fa-images', category='Website',
            list_fields=[('category', 'Category'), ('caption', 'Caption'), ('order', 'Order')],
            search_fields=['caption'],
            filter_fields=[('category', 'Category')],
            form_fields=['category', 'image', 'caption', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='contact-messages', model=ContactMessage, label='Contact Messages', singular='Message',
            icon='fa-solid fa-envelope-open-text', category='Website',
            list_fields=[('name', 'Name'), ('subject', 'Subject'), ('email', 'Email'),
                         ('is_read', 'Read'), ('submitted_at', 'Received')],
            search_fields=['name', 'email', 'message'],
            filter_fields=[('is_read', 'Read')],
            form_fields=['name', 'email', 'subject', 'message', 'is_read'],
        ),
        ManagedModel(
            slug='academic-sessions', model=AcademicSession, label='Academic Sessions', singular='Academic Session',
            icon='fa-solid fa-calendar-days', category='Student Records',
            list_fields=[('name', 'Session'), ('registration_open', 'Registration Open')],
            search_fields=['name'],
            filter_fields=[('registration_open', 'Registration Open')],
            form_fields=['name', 'registration_open'],
        ),
        ManagedModel(
            slug='courses', model=Course, label='Courses', singular='Course',
            icon='fa-solid fa-book', category='Student Records',
            list_fields=[('code', 'Code'), ('title', 'Title'), ('units', 'Units'), ('level', 'Level'),
                         ('semester', 'Semester'), ('programme', 'Programme'), ('lecturer_name', 'Lecturer')],
            search_fields=['code', 'title'],
            filter_fields=[('programme', 'Programme'), ('semester', 'Semester'), ('level', 'Level')],
            form_fields=['code', 'title', 'units', 'level', 'semester', 'programme', 'lecturer_name'],
        ),
        ManagedModel(
            slug='course-registrations', model=CourseRegistration, label='Course Registrations', singular='Registration',
            icon='fa-solid fa-clipboard-check', category='Student Records',
            list_fields=[('student', 'Student'), ('course', 'Course'), ('session', 'Session')],
            search_fields=['student__student_id', 'course__code'],
            filter_fields=[('session', 'Session')],
            form_fields=['student', 'course', 'session'],
        ),
        ManagedModel(
            # Bulk entry normally goes through the Gradesheets flow (Excel
            # download/upload + review + publish — admin_console/views.py's
            # gradesheet_* views); this generic entry is for one-off
            # corrections outside that flow.
            slug='results', model=Result, label='Results', singular='Result',
            icon='fa-solid fa-file-lines', category='Student Records',
            list_fields=[('student', 'Student'), ('course', 'Course'), ('ca_score', 'CA'), ('exam_score', 'Exam'),
                         ('score', 'Total'), ('grade', 'Grade'), ('session', 'Session'), ('is_published', 'Published')],
            search_fields=['student__student_id', 'student__surname', 'course__code'],
            filter_fields=[('session', 'Session'), ('semester', 'Semester'), ('is_published', 'Published')],
            form_fields=['student', 'course', 'ca_score', 'exam_score', 'semester', 'session', 'is_published'],
        ),
        ManagedModel(
            slug='attendance-records', model=AttendanceRecord, label='Attendance Records', singular='Attendance Record',
            icon='fa-solid fa-calendar-check', category='Student Records',
            list_fields=[('student', 'Student'), ('course', 'Course'), ('date', 'Date'), ('status', 'Status')],
            search_fields=['student__student_id', 'course__code'],
            filter_fields=[('status', 'Status'), ('session', 'Session')],
            form_fields=['student', 'course', 'date', 'status'],
        ),
        ManagedModel(
            slug='assignments', model=Assignment, label='Assignments', singular='Assignment',
            icon='fa-solid fa-clipboard-list', category='Student Records',
            list_fields=[('course', 'Course'), ('title', 'Title'), ('due_date', 'Due Date')],
            search_fields=['title'],
            filter_fields=[('course', 'Course')],
            form_fields=['course', 'title', 'description', 'due_date'],
            ordering='due_date',
        ),
        ManagedModel(
            slug='timetable', model=TimetableEntry, label='Timetable', singular='Timetable Entry',
            icon='fa-solid fa-table-cells', category='Student Records',
            list_fields=[('programme', 'Programme'), ('day', 'Day'), ('start_time', 'Time'),
                         ('course', 'Course'), ('venue', 'Venue')],
            filter_fields=[('programme', 'Programme'), ('day', 'Day')],
            form_fields=['programme', 'day', 'start_time', 'course', 'lecturer_name', 'venue'],
        ),
        ManagedModel(
            # amount isn't a real field — it's the sum of this structure's
            # FeeStructureItem rows (see students.models.FeeStructure.amount),
            # so it's list-only here; the breakdown itself is managed via
            # the 'fee-structure-items' entry below.
            slug='fee-structures', model=FeeStructure, label='Fee Structures', singular='Fee Structure',
            icon='fa-solid fa-sack-dollar', category='Student Records',
            list_fields=[('programme', 'Programme'), ('session', 'Session'), ('amount', 'Total Amount')],
            filter_fields=[('programme', 'Programme'), ('session', 'Session')],
            form_fields=['programme', 'session'],
        ),
        ManagedModel(
            slug='fee-structure-items', model=FeeStructureItem, label='Fee Breakdown Items', singular='Fee Item',
            icon='fa-solid fa-list-ul', category='Student Records',
            list_fields=[('fee_structure', 'Fee Structure'), ('category', 'Category'), ('label', 'Description'),
                         ('amount', 'Amount'), ('note', 'Note'), ('order', 'Order')],
            search_fields=['label', 'category'],
            filter_fields=[('fee_structure', 'Fee Structure')],
            form_fields=['fee_structure', 'category', 'label', 'amount', 'note', 'order'],
            ordering='order',
        ),
        ManagedModel(
            slug='student-announcements', model=Announcement, label='Announcements', singular='Announcement',
            icon='fa-solid fa-bullhorn', category='Student Records',
            list_fields=[('title', 'Title'), ('audience', 'Audience'), ('created_at', 'Created')],
            search_fields=['title', 'body'],
            filter_fields=[('audience', 'Audience')],
            form_fields=['title', 'body', 'audience'],
        ),
        ManagedModel(
            # Not in any role's 'manage'/'view' set (admin_console/permissions.py),
            # so restricted roles never see or reach this slug — only full-access
            # staff can assign roles, with zero extra view code needed for that.
            slug='staff-roles', model=StaffProfile, label='Staff Roles', singular='Staff Role',
            icon='fa-solid fa-user-shield', category='System',
            list_fields=[('user', 'User'), ('role', 'Role')],
            search_fields=['user__username', 'user__first_name', 'user__last_name', 'user__email'],
            filter_fields=[('role', 'Role')],
            form_fields=['user', 'role'],
            ordering='user__username',
        ),
    ]
    return {entry.slug: entry for entry in entries}


REGISTRY = _build_registry()


def categories():
    """REGISTRY entries grouped by category, in first-seen order — drives
    both the sidebar nav and the console home page."""
    grouped = {}
    for entry in REGISTRY.values():
        grouped.setdefault(entry.category, []).append(entry)
    return grouped
