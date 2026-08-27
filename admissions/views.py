from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from admissions.forms import ApplicationForm
from admissions.models import AdmissionCycle, Application, get_or_create_application


def apply(request):
    """
    Cold entry point for "Apply Now" — anonymous visitors get sent to
    register, everyone already signed in lands on their dashboard (the
    persistent hub for the rest of the flow).
    """
    cycle = AdmissionCycle.current()
    if not cycle:
        return render(request, 'admissions/closed.html')

    if not request.user.is_authenticated:
        return redirect('accounts:register')

    return redirect('admissions:dashboard')


@login_required(login_url='accounts:login')
def dashboard(request):
    """
    The applicant's persistent home once logged in — reachable regardless
    of payment/submission status (never a forced redirect chain). Shows
    the fee/payment banner, progress checklist and payment history inline;
    "Continue Application" / "Pay Now" are just actions from here rather
    than separate pages you get bounced into.
    """
    cycle = AdmissionCycle.current()
    application = get_or_create_application(request.user)

    invoice = None
    if application:
        from payments.models import get_or_create_invoice
        invoice = get_or_create_invoice(application)

    progress = None
    tracker = None
    if application and invoice and invoice.is_paid:
        if application.is_submitted:
            tracker = application.get_status_tracker()
        else:
            progress = application.get_progress()

    return render(request, 'admissions/dashboard.html', {
        'page': 'apply',
        'cycle': cycle,
        'application': application,
        'invoice': invoice,
        'progress': progress,
        'tracker': tracker,
        'payment_required': bool(invoice and not invoice.is_paid),
    })


@login_required(login_url='accounts:login')
def apply_form(request):
    """The actual 6-section application wizard — one combined form, gated
    on having a paid, not-yet-submitted application."""
    application = getattr(request.user, 'application', None)
    if not application:
        return redirect('admissions:dashboard')

    invoice = getattr(application, 'invoice', None)
    if not invoice or not invoice.is_paid:
        messages.info(request, 'Please pay your application fee first.')
        return redirect('admissions:dashboard')

    if application.is_submitted:
        return redirect('admissions:apply_success', application_number=application.application_number)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.is_submitted = True
            application.submitted_at = timezone.now()
            application.status = 'pending'
            application.save()
            messages.success(request, 'Your application has been submitted!')
            return redirect('admissions:apply_success', application_number=application.application_number)
    else:
        form = ApplicationForm(instance=application)

    return render(request, 'admissions/apply.html', {'page': 'apply', 'form': form, 'application': application})


@login_required(login_url='accounts:login')
def apply_success(request, application_number):
    application = get_object_or_404(Application, application_number=application_number, applicant=request.user)
    return render(request, 'admissions/apply_success.html', {'page': 'apply', 'application': application})
