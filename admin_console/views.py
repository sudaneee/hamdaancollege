from functools import partial, wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required as _staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.forms import modelform_factory
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from admin_console import permissions
from admin_console.registry import REGISTRY, categories
from admin_console.utils import filter_lookup_value, filter_options, querystring_without_page, resolve_value
from admissions.models import STATUS_CHOICES, AdmissionCycle, Application
from payments.models import ApplicationInvoice, ApplicationPayment, StudentInvoice, StudentPayment
from website.models import ContactMessage
from website.models import AboutContent, SiteSettings

# The console lives behind its own Staff Portal login — separate from the
# Applicant Portal (accounts:login) and not Django admin's own login
# screen either (staff_member_required defaults to 'admin:login').
staff_member_required = partial(_staff_member_required, login_url='accounts:staff_login')


def full_access_required(view_func):
    """Guards a dedicated (non-registry) view to full-access staff only —
    applied to everything no restricted role currently reaches at all:
    Users & Access, Site Settings, Support Tickets, etc. Stack under
    @staff_member_required so auth is checked first."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not permissions.is_full_access(request.user):
            messages.error(request, "You don't have access to that part of the console.")
            return redirect('admin_console:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def dedicated_required(name, manage=False):
    """Guards a dedicated (non-registry) view by permission name —
    e.g. Applications (Registrar), Invoices/Payments (Bursar). With
    manage=False (the default) requires view access; manage=True requires
    the stronger 'dedicated_manage' permission (real actions, not just
    looking). Stack under @staff_member_required."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            allowed = (
                permissions.can_manage_dedicated(request.user, name) if manage
                else permissions.can_view_dedicated(request.user, name)
            )
            if not allowed:
                messages.error(request, "You don't have access to that part of the console.")
                return redirect('admin_console:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _entry_or_404(slug):
    entry = REGISTRY.get(slug)
    if not entry:
        raise Http404(f'No manageable model registered for "{slug}".')
    return entry


# ── Home ──────────────────────────────────────────────────────────────────────

@staff_member_required
def console_home(request):
    """Landing page — key numbers at a glance, plus every registered
    module grouped by category (generic modules) and the hand-built ones
    (Applications/Invoices/Payments/Users/Settings) that aren't generic.
    A restricted role (e.g. Exam Officer) gets a cut-down version of this
    page instead — just the modules their role can actually reach."""
    if not permissions.is_full_access(request.user):
        visible = permissions.visible_slugs(request.user)
        role_categories = {
            category: [(entry, entry.model.objects.count()) for entry in entries if entry.slug in visible]
            for category, entries in categories().items()
        }
        role_categories = {c: entries for c, entries in role_categories.items() if entries}

        # Dedicated (non-registry) sections this role can at least view —
        # e.g. Applications/Students for Registrar, Invoices/Payments for Bursar.
        dedicated_sections = [
            ('applications', 'admin_console:applications_list', 'Applications', 'fa-solid fa-file-signature'),
            ('students', 'admin_console:students_list', 'Students', 'fa-solid fa-user-graduate'),
            ('gradesheets', 'admin_console:gradesheets_list', 'Gradesheets', 'fa-solid fa-file-excel'),
            ('invoices', 'admin_console:invoices_list', 'Invoices', 'fa-solid fa-file-invoice-dollar'),
            ('payments', 'admin_console:payments_list', 'Payments', 'fa-solid fa-credit-card'),
            ('student-invoices', 'admin_console:student_invoices_list', 'Student Invoices', 'fa-solid fa-file-invoice-dollar'),
            ('student-payments', 'admin_console:student_payments_list', 'Student Payments', 'fa-solid fa-credit-card'),
        ]
        dedicated_links = [
            {'url': reverse(url_name), 'label': label, 'icon': icon}
            for name, url_name, label, icon in dedicated_sections
            if permissions.can_view_dedicated(request.user, name)
        ]

        return render(request, 'admin_console/role_home.html', {
            'categories': role_categories, 'dedicated_links': dedicated_links, 'active_nav': 'console',
        })

    current_cycle = AdmissionCycle.current()
    total_applications = Application.objects.filter(is_submitted=True).count()
    pending_review = Application.objects.filter(is_submitted=True, status='pending').count()
    revenue = ApplicationPayment.objects.filter(status='success').aggregate(t=Sum('amount'))['t'] or 0
    unread_messages = ContactMessage.objects.filter(is_read=False).count()

    recent_applications = Application.objects.filter(is_submitted=True).order_by('-submitted_at')[:5]
    recent_messages = ContactMessage.objects.order_by('-submitted_at')[:5]

    # Model classes are callable, so `entry.model.objects.count` in a
    # template would have Django's auto-call resolution invoke the class
    # itself (constructing an instance) before reaching `.objects` — count
    # here instead, where `entry.model` is never asked to render alone.
    categories_with_counts = {
        category: [(entry, entry.model.objects.count()) for entry in entries]
        for category, entries in categories().items()
    }

    return render(request, 'admin_console/home.html', {
        'categories': categories_with_counts, 'active_nav': 'console',
        'current_cycle': current_cycle,
        'total_applications': total_applications,
        'pending_review': pending_review,
        'revenue': revenue,
        'unread_messages': unread_messages,
        'recent_applications': recent_applications,
        'recent_messages': recent_messages,
    })


# ── Generic CRUD ──────────────────────────────────────────────────────────────

@staff_member_required
def generic_list(request, slug):
    entry = _entry_or_404(slug)
    if not permissions.can_view(request.user, slug):
        messages.error(request, "You don't have access to that part of the console.")
        return redirect('admin_console:home')
    qs = entry.model.objects.all()
    if entry.ordering:
        qs = qs.order_by(entry.ordering)

    q = request.GET.get('q', '').strip()
    if q and entry.search_fields:
        query = Q()
        for f in entry.search_fields:
            query |= Q(**{f'{f}__icontains': q})
        qs = qs.filter(query)

    active_filters = {}
    for field_name, _ in entry.filter_fields:
        val = request.GET.get(field_name)
        if val:
            qs = qs.filter(**{field_name: filter_lookup_value(entry.model, field_name, val)})
            active_filters[field_name] = val

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    rows = [
        {'obj': obj, 'cells': [{'label': label, 'value': resolve_value(obj, path)} for path, label in entry.list_fields]}
        for obj in page_obj
    ]

    return render(request, 'admin_console/list.html', {
        'entry': entry, 'page_obj': page_obj, 'rows': rows, 'q': q,
        'active_filters': active_filters,
        'filters': [(name, label, filter_options(entry.model, name), active_filters.get(name, ''))
                    for name, label in entry.filter_fields],
        'active_nav': 'console', 'active_slug': slug, 'querystring': querystring_without_page(request),
        'can_manage': permissions.can_manage(request.user, slug),
    })


@staff_member_required
def generic_create(request, slug):
    entry = _entry_or_404(slug)
    if not permissions.can_manage(request.user, slug):
        messages.error(request, "You don't have access to add a new " + entry.singular.lower() + '.')
        return redirect('admin_console:list', slug=slug)
    Form = modelform_factory(entry.model, fields=entry.form_fields)
    if request.method == 'POST':
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'{entry.singular} created.')
            return redirect('admin_console:list', slug=slug)
    else:
        form = Form()
    return render(request, 'admin_console/form.html', {
        'entry': entry, 'form': form, 'mode': 'create', 'active_nav': 'console', 'active_slug': slug,
    })


@staff_member_required
def generic_edit(request, slug, pk):
    entry = _entry_or_404(slug)
    if not permissions.can_manage(request.user, slug):
        messages.error(request, "You don't have access to edit that " + entry.singular.lower() + '.')
        return redirect('admin_console:list', slug=slug)
    instance = get_object_or_404(entry.model, pk=pk)
    Form = modelform_factory(entry.model, fields=entry.form_fields)
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'{entry.singular} updated.')
            return redirect('admin_console:list', slug=slug)
    else:
        form = Form(instance=instance)
    return render(request, 'admin_console/form.html', {
        'entry': entry, 'form': form, 'mode': 'edit', 'instance': instance, 'active_nav': 'console', 'active_slug': slug,
    })


@staff_member_required
def generic_delete(request, slug, pk):
    entry = _entry_or_404(slug)
    if not permissions.can_manage(request.user, slug):
        messages.error(request, "You don't have access to delete that " + entry.singular.lower() + '.')
        return redirect('admin_console:list', slug=slug)
    if not entry.can_delete:
        raise Http404(f'{entry.label} cannot be deleted from the console.')
    instance = get_object_or_404(entry.model, pk=pk)
    if request.method == 'POST':
        label = str(instance)
        instance.delete()
        messages.success(request, f'{entry.singular} "{label}" deleted.')
        return redirect('admin_console:list', slug=slug)
    return render(request, 'admin_console/confirm_delete.html', {
        'entry': entry, 'instance': instance, 'active_nav': 'console', 'active_slug': slug,
    })


# ── Applications — dedicated, not generic: status changes must go through
# Application.set_status() so the status log stays intact. ───────────────────

@staff_member_required
@dedicated_required('applications')
def applications_list(request):
    qs = Application.objects.filter(is_submitted=True).select_related('programme', 'cycle').order_by('-submitted_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(application_number__icontains=q) | Q(surname__icontains=q) |
            Q(first_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    cycle_id = request.GET.get('cycle', '')
    if cycle_id:
        qs = qs.filter(cycle_id=cycle_id)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/applications.html', {
        'page_obj': page_obj, 'q': q, 'status': status, 'cycle_id': cycle_id,
        'status_choices': STATUS_CHOICES, 'cycles': AdmissionCycle.objects.all(),
        'active_nav': 'console', 'active_slug': 'applications',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@dedicated_required('applications')
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk, is_submitted=True)
    can_edit = permissions.can_manage_dedicated(request.user, 'applications')
    if request.method == 'POST' and can_edit:
        new_status = request.POST.get('status')
        if new_status in dict(STATUS_CHOICES):
            application.set_status(
                new_status, note=f'Marked {dict(STATUS_CHOICES)[new_status]} via Console.',
                user=request.user,
            )
            messages.success(request, f'Application marked as {application.get_status_display()}.')
            return redirect('admin_console:application_detail', pk=pk)
        messages.error(request, 'Invalid status.')

    return render(request, 'admin_console/application_detail.html', {
        'application': application, 'status_choices': STATUS_CHOICES,
        'status_logs': application.status_logs.order_by('-created_at'),
        'invoice': getattr(application, 'invoice', None),
        'student_record': getattr(application, 'student_record', None),
        'can_edit': can_edit,
        'active_nav': 'console', 'active_slug': 'applications',
    })


@staff_member_required
@dedicated_required('applications', manage=True)
@require_POST
def admit_as_student(request, pk):
    """Promotes an approved Application into a Student — same login the
    applicant already used to apply becomes their student login."""
    from students.models import Student

    application = get_object_or_404(Application, pk=pk, is_submitted=True)
    if application.status != 'approved':
        messages.error(request, 'Only approved applications can be admitted as students.')
        return redirect('admin_console:application_detail', pk=pk)
    if hasattr(application, 'student_record'):
        messages.info(request, 'This applicant has already been admitted as a student.')
        return redirect('admin_console:application_detail', pk=pk)

    student = Student.objects.create(
        user=application.applicant, application=application,
        surname=application.surname, first_name=application.first_name, middle_name=application.middle_name,
        gender=application.gender, phone=application.phone, email=application.email,
        address=application.address, state=application.state_of_origin, lga=application.lga,
        programme=application.programme, session=application.cycle.session,
    )
    messages.success(request, f'{student.full_name} admitted as student — ID {student.student_id}.')
    return redirect('admin_console:student_detail', pk=student.pk)


# ── Invoices / Payments — read-only in the console; invoices are frozen
# snapshots, payments only ever change via ZainPay verify/webhook/reconcile. ──

@staff_member_required
@dedicated_required('invoices')
def invoices_list(request):
    qs = ApplicationInvoice.objects.select_related('application').order_by('-generated_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(invoice_number__icontains=q) | Q(application__application_number__icontains=q) |
            Q(application__surname__icontains=q) | Q(application__first_name__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/invoices_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': ApplicationInvoice.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'invoices',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@dedicated_required('payments')
def payments_list(request):
    qs = ApplicationPayment.objects.select_related('invoice__application').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) | Q(gateway_reference__icontains=q) | Q(receipt_number__icontains=q) |
            Q(invoice__application__application_number__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/payments_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': ApplicationPayment.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'payments',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@dedicated_required('payments')
@require_POST
def payment_check_status(request, pk):
    from payments import zainpay

    payment = get_object_or_404(ApplicationPayment, pk=pk)
    try:
        result = zainpay.process_payment(payment)
        messages.success(request, f'Payment status: {result["status"]}.')
    except zainpay.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')

    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:payments_list')}{'?' + qs if qs else ''}")


# ── Users — staff account management (applicants keep using the public
# accounts app; this is for granting/revoking console access itself). ────────

@staff_member_required
@full_access_required
def users_list(request):
    qs = User.objects.all().order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    role = request.GET.get('role', '')
    if role == 'staff':
        qs = qs.filter(is_staff=True)
    elif role == 'applicant':
        qs = qs.filter(is_staff=False)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/users_list.html', {
        'page_obj': page_obj, 'q': q, 'role': role,
        'active_nav': 'console', 'active_slug': 'users',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@full_access_required
def user_create(request):
    Form = modelform_factory(
        User, fields=['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser', 'is_active'],
    )
    if request.method == 'POST':
        form = Form(request.POST)
        password = request.POST.get('password', '')
        if form.is_valid() and password:
            user = form.save(commit=False)
            user.set_password(password)
            user.save()
            messages.success(request, f'{user.username} created.')
            return redirect('admin_console:users_list')
        if not password:
            messages.error(request, 'A password is required.')
    else:
        form = Form(initial={'is_staff': True})
    return render(request, 'admin_console/user_form.html', {
        'form': form, 'mode': 'create', 'active_nav': 'console', 'active_slug': 'users',
    })


@staff_member_required
@full_access_required
@require_POST
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You can't deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        messages.success(request, f"{target.username} is now {'active' if target.is_active else 'inactive'}.")
    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:users_list')}{'?' + qs if qs else ''}")


@staff_member_required
@full_access_required
@require_POST
def user_toggle_staff(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You can't change your own staff status.")
    else:
        target.is_staff = not target.is_staff
        target.save(update_fields=['is_staff'])
        messages.success(request, f"{target.username} {'now has' if target.is_staff else 'no longer has'} console access.")
    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:users_list')}{'?' + qs if qs else ''}")


# ── Singletons — Site Settings & About Page Content ──────────────────────────

@staff_member_required
@full_access_required
def site_settings_edit(request):
    instance = SiteSettings.load()
    exclude = ['id']
    Form = modelform_factory(SiteSettings, exclude=exclude)
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Site settings updated.')
            return redirect('admin_console:site_settings')
    else:
        form = Form(instance=instance)
    return render(request, 'admin_console/singleton_form.html', {
        'form': form, 'title': 'Site Settings', 'active_nav': 'console', 'active_slug': 'site-settings',
    })


@staff_member_required
@full_access_required
def about_content_edit(request):
    instance = AboutContent.load()
    Form = modelform_factory(AboutContent, exclude=['id'])
    if request.method == 'POST':
        form = Form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'About page content updated.')
            return redirect('admin_console:about_content')
    else:
        form = Form(instance=instance)
    return render(request, 'admin_console/singleton_form.html', {
        'form': form, 'title': 'About Page Content', 'active_nav': 'console', 'active_slug': 'about-content',
    })


# ── Students — dedicated: editing goes through a small hand-picked field
# set (not every Student field makes sense to hand-edit), and the detail
# page pulls together results/attendance/fees that live on other models. ──

@staff_member_required
def students_list(request):
    from students.models import STATUS_CHOICES as STUDENT_STATUS_CHOICES
    from students.models import Student

    if not permissions.can_view_dedicated(request.user, 'students'):
        messages.error(request, "You don't have access to that part of the console.")
        return redirect('admin_console:home')

    qs = Student.objects.select_related('programme', 'user').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(student_id__icontains=q) | Q(surname__icontains=q) |
            Q(first_name__icontains=q) | Q(email__icontains=q)
        )
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/students_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': STUDENT_STATUS_CHOICES,
        'active_nav': 'console', 'active_slug': 'students',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
def student_detail(request, pk):
    from students.models import Student

    if not permissions.can_view_dedicated(request.user, 'students'):
        messages.error(request, "You don't have access to that part of the console.")
        return redirect('admin_console:home')

    can_edit = permissions.can_manage_dedicated(request.user, 'students')
    student = get_object_or_404(Student, pk=pk)
    Form = modelform_factory(Student, fields=[
        'surname', 'first_name', 'middle_name', 'gender', 'phone', 'email', 'address', 'state', 'lga',
        'programme', 'level', 'session', 'status',
    ])
    if request.method == 'POST' and can_edit:
        form = Form(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student record updated.')
            return redirect('admin_console:student_detail', pk=pk)
    else:
        form = Form(instance=student)

    return render(request, 'admin_console/student_detail.html', {
        'student': student, 'form': form, 'can_edit': can_edit,
        'results': student.results.select_related('course').order_by('-session'),
        'submissions': student.submissions.select_related('assignment').order_by('-submitted_at'),
        'invoice': student.invoices.filter(session=student.session).first(),
        'active_nav': 'console', 'active_slug': 'students',
    })


# ── Student Invoices / Payments — same read-only + check-status pattern
# as the admission-fee equivalents above. ─────────────────────────────────

@staff_member_required
@dedicated_required('student-invoices')
def student_invoices_list(request):
    qs = StudentInvoice.objects.select_related('student').order_by('-generated_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(invoice_number__icontains=q) | Q(student__student_id__icontains=q))
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/student_invoices_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': StudentInvoice.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'student-invoices',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@dedicated_required('student-payments')
def student_payments_list(request):
    qs = StudentPayment.objects.select_related('invoice__student').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(invoice__student__student_id__icontains=q))
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/student_payments_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status,
        'status_choices': StudentPayment.STATUS_CHOICES, 'active_nav': 'console', 'active_slug': 'student-payments',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@dedicated_required('student-payments')
@require_POST
def student_payment_check_status(request, pk):
    from payments import zainpay

    payment = get_object_or_404(StudentPayment, pk=pk)
    try:
        result = zainpay.process_payment(payment)
        messages.success(request, f'Payment status: {result["status"]}.')
    except zainpay.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')
    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:student_payments_list')}{'?' + qs if qs else ''}")


# ── Support Tickets — list + a quick "Mark Resolved" action. ─────────────────

@staff_member_required
@full_access_required
def support_tickets_list(request):
    from students.models import SupportTicket

    qs = SupportTicket.objects.select_related('student').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/support_tickets_list.html', {
        'page_obj': page_obj, 'status': status, 'status_choices': SupportTicket.STATUS_CHOICES,
        'active_nav': 'console', 'active_slug': 'support-tickets',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@full_access_required
@require_POST
def support_ticket_resolve(request, pk):
    from students.models import SupportTicket

    ticket = get_object_or_404(SupportTicket, pk=pk)
    ticket.status = 'Resolved'
    ticket.save(update_fields=['status'])
    messages.success(request, 'Ticket marked resolved.')
    qs = request.POST.get('qs', '')
    return redirect(f"{reverse('admin_console:support_tickets_list')}{'?' + qs if qs else ''}")


# ── Assignment Submissions — read-only across all students; submitting
# itself only ever happens from the student portal. ──────────────────────────

@staff_member_required
@full_access_required
def submissions_list(request):
    from students.models import AssignmentSubmission

    qs = AssignmentSubmission.objects.select_related('assignment', 'student').order_by('-submitted_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(student__student_id__icontains=q) | Q(assignment__title__icontains=q))

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/submissions_list.html', {
        'page_obj': page_obj, 'q': q, 'active_nav': 'console', 'active_slug': 'submissions',
        'querystring': querystring_without_page(request),
    })


# ── Gradesheets — Excel-based bulk result entry: Exam Officer downloads a
# roster template per Course/Session, the filled sheet (CA + Exam scores)
# comes back from the lecturer, gets uploaded here, is reviewed on-screen,
# then published. See admin_console/gradesheets.py for the Excel plumbing. ──

@staff_member_required
@dedicated_required('gradesheets')
def gradesheets_list(request):
    from students.models import CourseRegistration, Result

    combos = (
        CourseRegistration.objects.values('session', 'course_id', 'course__code', 'course__title', 'course__semester')
        .annotate(registered_count=Count('id', distinct=True))
        .order_by('-session', 'course__code')
    )
    rows = []
    for combo in combos:
        results_qs = Result.objects.filter(course_id=combo['course_id'], session=combo['session'])
        entered = results_qs.count()
        published = results_qs.filter(is_published=True).count()
        if entered == 0:
            status = 'Not Started'
        elif published == entered:
            status = 'Published'
        else:
            status = 'Draft'
        rows.append({**combo, 'entered': entered, 'published': published, 'status': status})

    return render(request, 'admin_console/gradesheets_list.html', {
        'rows': rows, 'active_nav': 'console', 'active_slug': 'gradesheets',
    })


@staff_member_required
@dedicated_required('gradesheets')
def gradesheet_detail(request, session, course_id):
    from students.models import Course, CourseRegistration, Result

    course = get_object_or_404(Course, pk=course_id)
    registrations = (
        CourseRegistration.objects.filter(course=course, session=session)
        .select_related('student').order_by('student__student_id')
    )
    results_by_student = {r.student_id: r for r in Result.objects.filter(course=course, session=session)}
    roster = [{'student': reg.student, 'result': results_by_student.get(reg.student_id)} for reg in registrations]

    return render(request, 'admin_console/gradesheet_detail.html', {
        'course': course, 'session': session, 'roster': roster,
        'can_manage': permissions.can_manage_dedicated(request.user, 'gradesheets'),
        'active_nav': 'console', 'active_slug': 'gradesheets',
    })


@staff_member_required
@dedicated_required('gradesheets', manage=True)
def gradesheet_download(request, session, course_id):
    from io import BytesIO

    from admin_console.gradesheets import build_template
    from students.models import Course, Result

    course = get_object_or_404(Course, pk=course_id)
    results_by_student = {r.student_id: r for r in Result.objects.filter(course=course, session=session)}
    wb = build_template(course, session, results_by_student)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f'{course.code}_{session.replace("/", "-")}_gradesheet.xlsx'
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@staff_member_required
@dedicated_required('gradesheets', manage=True)
@require_POST
def gradesheet_upload(request, session, course_id):
    from admin_console.gradesheets import import_upload
    from students.models import Course

    course = get_object_or_404(Course, pk=course_id)
    file_obj = request.FILES.get('file')
    if not file_obj:
        messages.error(request, 'Choose a file to upload.')
        return redirect('admin_console:gradesheet_detail', session=session, course_id=course_id)

    outcome = import_upload(course, session, file_obj)
    if outcome.created or outcome.updated:
        messages.success(
            request,
            f'{outcome.created} result(s) added, {outcome.updated} updated — still draft, review below then publish.',
        )
    for error in outcome.errors[:10]:
        messages.error(request, error)
    if len(outcome.errors) > 10:
        messages.error(request, f'...and {len(outcome.errors) - 10} more row error(s).')
    if not outcome.created and not outcome.updated and not outcome.errors:
        messages.warning(request, 'No rows were found in that file.')

    return redirect('admin_console:gradesheet_detail', session=session, course_id=course_id)


@staff_member_required
@dedicated_required('gradesheets', manage=True)
@require_POST
def gradesheet_publish(request, session, course_id):
    from students.models import Course, Result

    course = get_object_or_404(Course, pk=course_id)
    updated = Result.objects.filter(course=course, session=session, is_published=False).update(
        is_published=True, published_at=timezone.now(),
    )
    if updated:
        messages.success(request, f'Published {updated} result(s) — now visible to students.')
    else:
        messages.info(request, 'Nothing to publish — every entered result is already published.')
    return redirect('admin_console:gradesheet_detail', session=session, course_id=course_id)


# ── Job Applications — dedicated: needs a resume download link and a
# status-change action, so it's not the plain generic CRUD scaffold
# (Job Postings themselves ARE generic — see the 'job-postings' registry
# entry). Full-access only for now — no existing role owns HR/careers. ──────

@staff_member_required
@full_access_required
def job_applications_list(request):
    from website.models import JobApplication, JobPosting

    qs = JobApplication.objects.select_related('job').order_by('-submitted_at')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(job__title__icontains=q))
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    job_id = request.GET.get('job', '')
    if job_id:
        qs = qs.filter(job_id=job_id)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_console/job_applications_list.html', {
        'page_obj': page_obj, 'q': q, 'status': status, 'job_id': job_id,
        'status_choices': JobApplication.STATUS_CHOICES, 'jobs': JobPosting.objects.all(),
        'active_nav': 'console', 'active_slug': 'job-applications',
        'querystring': querystring_without_page(request),
    })


@staff_member_required
@full_access_required
def job_application_detail(request, pk):
    from website.models import JobApplication

    application = get_object_or_404(JobApplication, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save(update_fields=['status'])
            messages.success(request, f'Application marked as {application.get_status_display()}.')
            return redirect('admin_console:job_application_detail', pk=pk)
        messages.error(request, 'Invalid status.')

    return render(request, 'admin_console/job_application_detail.html', {
        'application': application, 'status_choices': JobApplication.STATUS_CHOICES,
        'active_nav': 'console', 'active_slug': 'job-applications',
    })
