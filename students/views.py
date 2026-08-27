from django.contrib import messages
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Notification
from students.decorators import student_required
from students.models import (
    AcademicSession, Announcement, Assignment, AssignmentSubmission, AttendanceRecord,
    Course, CourseRegistration, SupportTicket, TimetableEntry,
)


def _day_name(date):
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][date.weekday()]


@student_required
def dashboard(request):
    student = request.user.student
    today = timezone.localdate()

    upcoming_classes = TimetableEntry.objects.filter(
        programme=student.programme, day=_day_name(today),
    ).select_related('course').order_by('start_time')[:3]
    if not upcoming_classes:
        upcoming_classes = TimetableEntry.objects.filter(programme=student.programme).select_related('course')[:3]

    submitted_ids = set(AssignmentSubmission.objects.filter(student=student).values_list('assignment_id', flat=True))
    upcoming_assignments = Assignment.objects.filter(
        course__programme=student.programme,
    ).exclude(pk__in=submitted_ids).order_by('due_date')[:3]

    recent_payments = student.invoices.first().payments.filter(status='success').order_by('-created_at')[:3] \
        if student.invoices.exists() else []

    announcements = Announcement.objects.exclude(audience='Staff')[:4]

    return render(request, 'students/dashboard.html', {
        'student': student, 'upcoming_classes': upcoming_classes, 'upcoming_assignments': upcoming_assignments,
        'recent_payments': recent_payments, 'announcements': announcements,
        'registered_courses_count': student.registrations.filter(session=student.session).count(),
        'active_nav': 'dashboard',
    })


@student_required
def profile(request):
    return render(request, 'students/profile.html', {'student': request.user.student, 'active_nav': 'profile'})


@student_required
def academics(request):
    return render(request, 'students/academics.html', {'student': request.user.student, 'active_nav': 'academics'})


@student_required
def course_registration_dashboard(request):
    """Landing page: past registrations grouped by session (click through
    to the detail view for any of them), plus the entry point into a new
    registration for whichever session is currently open."""
    student = request.user.student

    session_summaries = (
        CourseRegistration.objects.filter(student=student)
        .values('session').annotate(course_count=Count('id')).order_by('-session')
    )

    academic_session = AcademicSession.objects.filter(name=student.session).first()
    registration_open = bool(academic_session and academic_session.registration_open)
    invoice = student.current_invoice
    fees_paid = bool(invoice and invoice.is_paid)
    already_registered = CourseRegistration.objects.filter(student=student, session=student.session).exists()

    return render(request, 'students/course_registration_dashboard.html', {
        'student': student, 'session_summaries': session_summaries,
        'registration_open': registration_open, 'fees_paid': fees_paid,
        'already_registered': already_registered, 'active_nav': 'courses',
    })


@student_required
def course_registration_detail(request, session):
    student = request.user.student
    registrations = CourseRegistration.objects.filter(student=student, session=session).select_related('course')
    if not registrations.exists():
        raise Http404('No course registration found for that session.')

    return render(request, 'students/course_registration_detail.html', {
        'student': student, 'session': session,
        'first_semester': registrations.filter(course__semester='First'),
        'second_semester': registrations.filter(course__semester='Second'),
        'active_nav': 'courses',
    })


@student_required
def course_registration_form(request):
    """The actual registration — courses from every programme in the
    student's department, at their level, split by semester. Editable any
    time the session stays open (adjusting just diffs the selection
    against what's already registered, nothing is one-shot/locked)."""
    from payments.models import get_or_create_student_invoice

    student = request.user.student

    academic_session = AcademicSession.objects.filter(name=student.session).first()
    if not academic_session or not academic_session.registration_open:
        messages.error(request, 'Course registration is not currently open for your session.')
        return redirect('students:courses')

    invoice = get_or_create_student_invoice(student)
    if not invoice.is_paid:
        messages.error(request, 'Please pay your session fees before registering for courses.')
        return redirect('students:fees')

    if not student.programme or not student.programme.department:
        messages.error(request, "Your programme/department isn't set — contact the Admissions Office.")
        return redirect('students:courses')

    available_courses = Course.objects.filter(
        programme__department=student.programme.department, level=student.level,
    ).select_related('programme').order_by('semester', 'code')

    if request.method == 'POST':
        selected_ids = {int(pk) for pk in request.POST.getlist('courses') if pk.isdigit()}
        CourseRegistration.objects.filter(
            student=student, session=student.session,
        ).exclude(course_id__in=selected_ids).delete()
        for course_id in selected_ids:
            CourseRegistration.objects.get_or_create(student=student, course_id=course_id, session=student.session)
        messages.success(request, 'Course registration saved.')
        return redirect('students:courses')

    registered_ids = set(CourseRegistration.objects.filter(
        student=student, session=student.session,
    ).values_list('course_id', flat=True))

    return render(request, 'students/course_registration_form.html', {
        'student': student,
        'first_semester': [c for c in available_courses if c.semester == 'First'],
        'second_semester': [c for c in available_courses if c.semester == 'Second'],
        'registered_ids': registered_ids, 'active_nav': 'courses',
    })


@student_required
def results(request):
    """Landing page: every session/semester combo that has published
    results, newest first — click through to see the full breakdown.
    Mirrors course_registration_dashboard's session-history pattern."""
    student = request.user.student
    combos = (
        student.results.filter(is_published=True).values_list('session', 'semester').distinct()
        .order_by('-session', 'semester')
    )
    groups = [{
        'session': session, 'semester': semester,
        'course_count': student.results.filter(session=session, semester=semester, is_published=True).count(),
        'gpa': student.gpa_for(session, semester),
    } for session, semester in combos]
    return render(request, 'students/results.html', {
        'student': student, 'groups': groups, 'active_nav': 'results',
    })


@student_required
def result_detail(request, session, semester):
    student = request.user.student
    result_rows = student.results_for(session, semester)
    if not result_rows.exists():
        raise Http404('No results found for that session and semester.')
    return render(request, 'students/result_detail.html', {
        'student': student, 'session': session, 'semester': semester,
        'results': result_rows, 'gpa': student.gpa_for(session, semester),
        'active_nav': 'results',
    })


@student_required
def attendance(request):
    student = request.user.student
    course_ids = CourseRegistration.objects.filter(student=student, session=student.session).values_list('course_id', flat=True)
    rows = []
    for course_id in course_ids:
        records = AttendanceRecord.objects.filter(student=student, course_id=course_id, session=student.session)
        total = records.count()
        present = records.filter(status='Present').count()
        rows.append({
            'course': records.first().course if records.exists() else None,
            'classes': total, 'present': present, 'absent': total - present,
            'percentage': round(present / total * 100) if total else 0,
        })
    rows = [r for r in rows if r['course']]
    return render(request, 'students/attendance.html', {'student': student, 'rows': rows, 'active_nav': 'attendance'})


@student_required
def timetable(request):
    student = request.user.student
    entries = list(TimetableEntry.objects.filter(programme=student.programme).select_related('course'))
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_slots = sorted({e.start_time for e in entries})

    by_day_time = {(e.day, e.start_time): e for e in entries}
    rows = [
        {'time': slot, 'cells': [by_day_time.get((day, slot)) for day in days]}
        for slot in time_slots
    ]
    return render(request, 'students/timetable.html', {
        'student': student, 'days': days, 'rows': rows, 'active_nav': 'timetable',
    })


@student_required
def assignments(request):
    student = request.user.student
    status_filter = request.GET.get('status', 'All')
    today = timezone.localdate()
    submitted_ids = set(AssignmentSubmission.objects.filter(student=student).values_list('assignment_id', flat=True))

    all_assignments = Assignment.objects.filter(course__programme=student.programme).select_related('course')
    rows = []
    for a in all_assignments:
        is_submitted = a.pk in submitted_ids
        overdue = not is_submitted and a.due_date < today
        status = 'Submitted' if is_submitted else 'Overdue' if overdue else 'Pending'
        rows.append({'assignment': a, 'status': status})

    if status_filter != 'All':
        rows = [r for r in rows if r['status'] == status_filter]

    return render(request, 'students/assignments.html', {
        'student': student, 'rows': rows, 'status_filter': status_filter, 'active_nav': 'assignments',
    })


@student_required
def submit_assignment(request, pk):
    if request.method != 'POST':
        return redirect('students:assignments')
    student = request.user.student
    assignment = get_object_or_404(Assignment, pk=pk, course__programme=student.programme)
    AssignmentSubmission.objects.get_or_create(
        assignment=assignment, student=student, defaults={'file': request.FILES.get('file')},
    )
    messages.success(request, f'"{assignment.title}" submitted successfully.')
    return redirect('students:assignments')


@student_required
def documents(request):
    """Uses the same document set an application produced (passport photo,
    O'Level result, birth certificate, ID) since there's no separate
    staff-issued-document model yet — everything shown here already
    really exists on disk."""
    student = request.user.student
    application = student.application
    return render(request, 'students/documents.html', {
        'student': student, 'application': application, 'active_nav': 'documents',
    })


@student_required
def announcements(request):
    items = Announcement.objects.exclude(audience='Staff')
    return render(request, 'students/announcements.html', {'items': items, 'active_nav': 'announcements'})


@student_required
def notifications_view(request):
    user_notifications = Notification.objects.filter(user=request.user)
    return render(request, 'students/notifications.html', {
        'notifications': user_notifications, 'active_nav': 'notifications',
    })


@student_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect('students:notifications')


@student_required
def delete_notification(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).delete()
    return redirect('students:notifications')


@student_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('students:notifications')


@student_required
def support(request):
    student = request.user.student
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        subject = request.POST.get('subject', 'Other')
        if not message:
            messages.error(request, 'Please describe your issue before submitting.')
        else:
            SupportTicket.objects.create(student=student, subject=subject, message=message)
            messages.success(request, 'Your support request has been submitted — our team will respond shortly.')
            return redirect('students:support')
    return render(request, 'students/support.html', {
        'student': student, 'subject_choices': SupportTicket.SUBJECT_CHOICES, 'active_nav': 'support',
    })


@student_required
def fees(request):
    """Landing page: every session with fees relevant to this student
    (a FeeStructure for their programme, or an invoice already on record),
    newest first — click through to a session's own detail/pay page.
    Mirrors course_registration_dashboard's session-history pattern."""
    from students.models import FeeStructure

    student = request.user.student
    fee_sessions = set(FeeStructure.objects.filter(programme=student.programme).values_list('session', flat=True))
    invoice_sessions = set(student.invoices.values_list('session', flat=True))
    all_sessions = sorted(fee_sessions | invoice_sessions, reverse=True)

    rows = []
    for session in all_sessions:
        invoice = student.invoices.filter(session=session).first()
        rows.append({
            'session': session, 'invoice': invoice,
            'is_paid': bool(invoice and invoice.is_paid),
            'registration_open': AcademicSession.objects.filter(name=session, registration_open=True).exists(),
        })

    return render(request, 'students/fees.html', {'student': student, 'rows': rows, 'active_nav': 'fees'})


@student_required
def fee_detail(request, session):
    from students.models import FeeStructure

    student = request.user.student
    invoice = student.invoices.filter(session=session).first()
    structure = FeeStructure.objects.filter(programme=student.programme, session=session).first()
    if not invoice and not structure:
        raise Http404('No fee record found for that session.')

    registration_open = AcademicSession.objects.filter(name=session, registration_open=True).exists()
    payments = invoice.payments.order_by('-created_at') if invoice else []

    return render(request, 'students/fee_detail.html', {
        'student': student, 'session': session, 'invoice': invoice, 'structure': structure,
        'payments': payments, 'registration_open': registration_open, 'active_nav': 'fees',
    })
