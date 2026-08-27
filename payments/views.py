"""
Payment views for the admission application fee.

Applicants aren't looked up by session/anonymous draft here (unlike
glittering) — they're always request.user, gated by @login_required, since
hamdaan's flow requires an account + verified email before payment.
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from admissions.models import get_or_create_application
from payments import zainpay
from payments.models import ApplicationPayment, StudentPayment, get_or_create_invoice, get_or_create_student_invoice

logger = logging.getLogger(__name__)


def find_payment_by_reference(reference):
    if not reference:
        return None
    payment = ApplicationPayment.objects.filter(reference=reference).first()
    if payment:
        return payment
    return StudentPayment.objects.filter(reference=reference).first()


@login_required(login_url='accounts:login')
def apply_payment(request):
    """
    The application fee must be paid before the form unlocks. Creates the
    draft Application + its invoice on first visit (fee snapshotted from
    the currently open AdmissionCycle) — same lazy-create the dashboard
    uses, so visiting either one first works identically.
    """
    application = get_or_create_application(request.user)
    if not application:
        messages.info(request, 'Admissions are currently closed.')
        return redirect('admissions:dashboard')

    if application.is_submitted:
        return redirect('admissions:apply_success', application_number=application.application_number)

    invoice = get_or_create_invoice(application)

    if invoice.is_paid:
        return redirect('admissions:dashboard')

    pending_payment = invoice.payments.filter(status='pending').order_by('-created_at').first()

    return render(request, 'payments/apply_payment.html', {
        'application': application, 'invoice': invoice, 'pending_payment': pending_payment,
    })


@login_required(login_url='accounts:login')
@require_POST
def initiate_application_payment(request):
    application = getattr(request.user, 'application', None)
    if not application:
        return redirect('admissions:dashboard')
    invoice = getattr(application, 'invoice', None)

    if not invoice or invoice.is_paid:
        messages.info(request, 'This application fee is already paid.')
        return redirect('payments:apply_payment')

    callback_url = request.build_absolute_uri(reverse('payments:zainpay_callback'))
    try:
        result = zainpay.initiate_payment(
            invoice=invoice, callback_url=callback_url, customer_email=application.applicant.email,
            mobile=application.phone or '08000000000',
        )
    except zainpay.ZainPayError as exc:
        logger.error('ZainPay initiate failed for %s: %s', application.application_number, exc)
        messages.error(request, f'Payment gateway error: {exc}')
        return redirect('payments:apply_payment')

    ApplicationPayment.objects.create(
        invoice=invoice, amount=invoice.balance, gateway='zainpay', status='pending',
        gateway_reference=result['gateway_reference'], reference=result['reference'],
    )
    return redirect(result['payment_url'])


@login_required(login_url='accounts:login')
@require_POST
def check_application_payment_status(request, payment_pk):
    application = getattr(request.user, 'application', None)
    if not application:
        return redirect('admissions:dashboard')
    payment = get_object_or_404(ApplicationPayment, pk=payment_pk, invoice__application=application)

    if payment.status == 'success':
        messages.info(request, 'This payment is already confirmed as successful.')
        return redirect('admissions:dashboard')

    try:
        result = zainpay.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, 'Payment confirmed!')
            return redirect('admissions:dashboard')
        messages.info(request, f'Payment status: {result["status"]}.')
    except zainpay.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')

    return redirect('payments:apply_payment')


# ── School fees (students) — one invoice per session; paying a given
# session's fees is only ever offered while that session's course
# registration is open (mirrors students.views.course_registration_form's
# own gate — the two are deliberately the same on/off switch). ──────────────

def _registration_open_for(session):
    from students.models import AcademicSession
    return AcademicSession.objects.filter(name=session, registration_open=True).exists()


@login_required(login_url='accounts:student_login')
def student_fee_payment(request, session):
    student = getattr(request.user, 'student', None)
    if not student:
        return redirect('students:dashboard')

    invoice = get_or_create_student_invoice(student, session=session)
    if invoice.is_paid:
        messages.info(request, 'These fees are already fully paid.')
    pending_payment = invoice.payments.filter(status='pending').order_by('-created_at').first()

    return render(request, 'payments/student_fee_payment.html', {
        'student': student, 'invoice': invoice, 'session': session,
        'pending_payment': pending_payment, 'registration_open': _registration_open_for(session),
        'active_nav': 'fees',
    })


@login_required(login_url='accounts:student_login')
@require_POST
def initiate_student_payment(request, session):
    student = getattr(request.user, 'student', None)
    if not student:
        return redirect('students:dashboard')

    if not _registration_open_for(session):
        messages.error(request, 'Fee payment for that session is not currently open.')
        return redirect('students:fee_detail', session=session)

    invoice = get_or_create_student_invoice(student, session=session)
    if invoice.is_paid:
        messages.info(request, 'This invoice is already fully paid.')
        return redirect('payments:student_fee_payment', session=session)

    callback_url = request.build_absolute_uri(reverse('payments:zainpay_callback'))
    try:
        result = zainpay.initiate_payment(
            invoice=invoice, callback_url=callback_url, customer_email=student.user.email,
            mobile=student.phone or '08000000000',
        )
    except zainpay.ZainPayError as exc:
        logger.error('ZainPay initiate failed for student %s: %s', student.student_id, exc)
        messages.error(request, f'Payment gateway error: {exc}')
        return redirect('payments:student_fee_payment', session=session)

    StudentPayment.objects.create(
        invoice=invoice, amount=invoice.balance, gateway='zainpay', status='pending',
        gateway_reference=result['gateway_reference'], reference=result['reference'],
    )
    return redirect(result['payment_url'])


@login_required(login_url='accounts:student_login')
@require_POST
def check_student_payment_status(request, payment_pk):
    student = getattr(request.user, 'student', None)
    if not student:
        return redirect('students:dashboard')
    payment = get_object_or_404(StudentPayment, pk=payment_pk, invoice__student=student)
    session = payment.invoice.session

    if payment.status == 'success':
        messages.info(request, 'This payment is already confirmed as successful.')
        return redirect('payments:student_fee_payment', session=session)

    try:
        result = zainpay.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, 'Payment confirmed!')
        else:
            messages.info(request, f'Payment status: {result["status"]}.')
    except zainpay.ZainPayError as exc:
        messages.error(request, f'Could not verify payment: {exc}')

    return redirect('payments:student_fee_payment', session=session)


@csrf_exempt
def zainpay_callback(request):
    """
    Dual-purpose endpoint:
      - POST, unauthenticated server push → ZainPay webhook.
      - GET → browser redirect back after the hosted checkout, verify + update.
    """
    if request.method == 'POST':
        return zainpay_webhook(request)

    txn_ref = request.GET.get('txnRef') or request.GET.get('reference')
    payment = find_payment_by_reference(txn_ref)
    if not payment:
        payment = ApplicationPayment.objects.filter(status='pending').order_by('-created_at').first()
    if not payment:
        messages.warning(request, 'No pending payment found to verify.')
        return redirect('website:home')

    try:
        result = zainpay.process_payment(payment)
        if result['status'] == 'success':
            messages.success(request, f'Payment of ₦{payment.amount:,.2f} confirmed. Thank you!')
        elif result['status'] == 'pending':
            messages.info(request, 'Payment is still processing — please check again shortly.')
        else:
            messages.error(request, 'Payment was not successful. Please try again.')
    except zainpay.ZainPayError as exc:
        logger.error('ZainPay verify failed for %s: %s', payment.reference, exc)
        messages.error(request, f'Could not verify payment: {exc}')

    if isinstance(payment, StudentPayment):
        if request.user.is_authenticated and getattr(request.user, 'student', None) == payment.invoice.student:
            return redirect('students:dashboard')
        return redirect('accounts:student_login')

    if request.user.is_authenticated and getattr(request.user, 'application', None) == payment.invoice.application:
        return redirect('admissions:dashboard')
    return redirect('accounts:login')


def zainpay_webhook(request):
    """
    Receives server-to-server deposit event notifications from ZainPay.
    Always returns 200 so ZainPay stops retrying — errors are logged only.
    """
    raw_body = request.body
    logger.info('ZainPay webhook received — body=%s', raw_body[:500])

    try:
        secret_key = getattr(settings, 'ZAINPAY_SECRET_KEY', '')
        if secret_key:
            received_sig = request.headers.get('Zainpay-Signature', '')
            expected_sig = hmac.new(secret_key.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, received_sig):
                logger.warning('ZainPay webhook: invalid signature received=%s', received_sig)
                return JsonResponse({'status': 'error', 'reason': 'invalid signature'}, status=400)

        if not raw_body:
            return JsonResponse({'status': 'ok', 'reason': 'empty body'}, status=200)

        try:
            payload = json.loads(raw_body)
        except (ValueError, TypeError):
            logger.warning('ZainPay webhook: non-JSON body — %s', raw_body[:300])
            return JsonResponse({'status': 'ok', 'reason': 'invalid JSON'}, status=200)

        event = payload.get('event') or payload.get('event_type', '')
        data = payload.get('data') or {}
        txn_ref = data.get('txnRef') or payload.get('txnRef', '')

        logger.info('ZainPay webhook event=%s txnRef=%s', event, txn_ref)

        if 'deposit' not in event:
            return JsonResponse({'status': 'ok', 'reason': f'event {event!r} not processed'}, status=200)
        if not txn_ref:
            return JsonResponse({'status': 'ok', 'reason': 'no txnRef'}, status=200)

        payment = find_payment_by_reference(txn_ref)
        if not payment:
            logger.warning('ZainPay webhook: no payment for txnRef=%s', txn_ref)
            return JsonResponse({'status': 'ok', 'reason': 'payment not found'}, status=200)

        if payment.status == 'success':
            return JsonResponse({'status': 'ok', 'reason': 'already confirmed'}, status=200)

        try:
            zainpay.process_payment(payment)
        except zainpay.ZainPayError as exc:
            logger.error('ZainPay webhook verify API error for %s: %s', txn_ref, exc)

    except Exception:
        logger.exception('ZainPay webhook unhandled error')

    return JsonResponse({'status': 'ok'}, status=200)
