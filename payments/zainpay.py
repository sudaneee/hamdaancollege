"""
ZainPay payment gateway — redirect flow.

Ported from glittering/payments/services.py (which itself was corrected
against ZainPay's own docs — https://zainpay.ng/developers/card-endpoints#card-integration-steps
— after live sandbox testing showed a naive port hitting the wrong verify
URL / parsing a response shape that doesn't exist). Trimmed here to only
know about admissions.ApplicationInvoice — glittering also supports a
finance.Payment (school fees) shape that hamdaan doesn't have yet.

1. POST /zainbox/card/initialize/payment        →  response.data is the redirect URL
2. Redirect the user to that URL
3. ZainPay redirects back to callBackUrl with ?txnRef=<ref>
4. GET /virtual-account/wallet/deposit/verify/v2/{txnRef}  →  confirm status
     Success: HTTP 200, a flat deposit record (amountAfterCharges, txnRef, ...)
     — there is no "code" field on success, unlike most other ZainPay endpoints.
     Ambiguous: HTTP 400 {"code":"04","description":"Txn not found",...} — the
     docs explicitly warn this same shape covers "still pending", "failed",
     AND "genuinely doesn't exist". Not distinguishable on its own.
5. When step 4 is ambiguous, GET
     /virtual-account/wallet/transaction/reconcile/card-payment?txnRef=<ref>
   forces ZainPay to resolve it — returns {"code":"00","data":{"txnStatus":
   "success"|"failed", ...}} once it can.

Sandbox base URL : https://sandbox.zainpay.ng
Live base URL    : https://api.zainpay.ng
Amount           : in Naira (not kobo) for these two endpoints; webhook
                    payloads report amounts in kobo instead (see the webhook
                    handler in payments/views.py).
"""

import logging
import uuid
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# A flat transaction charge passed on to whoever's paying, added only to the
# amount actually sent to ZainPay at checkout — never to what we display or
# record anywhere in our own invoices/payments (those stay exactly what's
# owed; ApplicationPayment.amount is set from invoice.balance at creation
# time and is never overwritten by ZainPay's post-charge figure).
ZAINPAY_TRANSACTION_CHARGE = Decimal('300')


class ZainPayError(Exception):
    pass


def _base_url() -> str:
    return getattr(settings, 'ZAINPAY_BASE_URL', 'https://sandbox.zainpay.ng').rstrip('/')


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ZAINPAY_PUBLIC_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def initiate_payment(invoice, callback_url: str, customer_email: str, mobile: str = '08000000000') -> dict:
    """
    Initialize a ZainPay redirect payment.

    Calls POST /zainbox/card/initialize/payment and returns:
        reference          — our unique txnRef (store on the ApplicationPayment record)
        gateway_reference  — same value, kept distinct for clarity elsewhere
        payment_url        — ZainPay hosted checkout page to redirect the user to
    """
    reference = f"HIC-{uuid.uuid4().hex[:12].upper()}"
    zainbox_code = getattr(settings, 'ZAINPAY_ZAINBOX_CODE', '')

    raw_amount = invoice.balance + ZAINPAY_TRANSACTION_CHARGE
    amount = str(int(raw_amount)) if raw_amount == int(raw_amount) else str(raw_amount)

    payload = {
        "amount": amount,
        "txnRef": reference,
        "mobileNumber": mobile,
        "emailAddress": customer_email,
        "zainboxCode": zainbox_code,
        "callBackUrl": callback_url,
        "paymentChannels": ["bank_transfer", "card"],
    }

    logger.info("ZainPay init — ref %s | amount %s | zainbox %s", reference, amount, zainbox_code)

    try:
        resp = requests.post(
            f"{_base_url()}/zainbox/card/initialize/payment",
            json=payload, headers=_headers(), timeout=30,
        )
    except requests.RequestException as exc:
        raise ZainPayError(f"Network error: {exc}") from exc

    raw = resp.text
    logger.info("ZainPay init response — %s — %s", resp.status_code, raw[:300])

    if not raw.strip():
        raise ZainPayError(f"Empty response from ZainPay (HTTP {resp.status_code})")

    try:
        result = resp.json()
    except ValueError:
        raise ZainPayError(f"Non-JSON response (HTTP {resp.status_code}): {raw[:300]}")

    data = result.get('data')
    if isinstance(data, str) and data.startswith('http'):
        payment_url = data
    elif isinstance(data, dict):
        payment_url = data.get('redirectUrl') or data.get('paymentUrl', '')
    else:
        payment_url = ''

    if not payment_url:
        raise ZainPayError(
            result.get('description') or result.get('message') or
            f"No redirect URL in ZainPay response: {result}"
        )

    return {'reference': reference, 'gateway_reference': reference, 'payment_url': payment_url}


def verify_payment(txn_ref: str) -> dict:
    """
    Verify a ZainPay payment by txnRef after the user is redirected back.
    Returns status ('success' | 'pending' | 'failed'), amount (Decimal naira).

    The primary endpoint's "not found" response is ambiguous by ZainPay's
    own admission (see module docstring) — when we hit it, fall back to the
    card-payment reconciliation endpoint for a definitive answer before
    settling for 'pending'.
    """
    url = f"{_base_url()}/virtual-account/wallet/deposit/verify/v2/{txn_ref}"

    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
    except requests.RequestException as exc:
        raise ZainPayError(f"Network error: {exc}") from exc

    raw = resp.text
    logger.info("ZainPay verify %s — HTTP %s — %s", txn_ref, resp.status_code, raw[:400])

    if not raw.strip():
        raise ZainPayError(f"Empty response from ZainPay (HTTP {resp.status_code})")

    try:
        result = resp.json()
    except ValueError:
        raise ZainPayError(f"Non-JSON response (HTTP {resp.status_code}): {raw[:300]}")

    # Success: HTTP 200 with the flat deposit record — no "code" field at all.
    if resp.status_code == 200 and 'txnRef' in result:
        try:
            amount = Decimal(str(result.get('amountAfterCharges', 0)))
        except Exception:
            amount = Decimal('0.00')
        return {'status': 'success', 'amount': amount, 'gateway_reference': txn_ref, 'raw_response': result}

    # Ambiguous response — ask the reconciliation endpoint for a definitive answer.
    reconciled = _reconcile_card_payment(txn_ref)
    if reconciled is not None:
        return reconciled

    return {'status': 'pending', 'amount': Decimal('0.00'), 'gateway_reference': txn_ref, 'raw_response': result}


def _reconcile_card_payment(txn_ref: str) -> dict | None:
    """
    GET /virtual-account/wallet/transaction/reconcile/card-payment?txnRef=...
    — forces ZainPay to resolve a stuck/ambiguous status. Returns a result
    dict when it gets a definitive success/failed answer, else None (the
    caller falls back to 'pending' and the applicant/cron can retry later).
    """
    url = f"{_base_url()}/virtual-account/wallet/transaction/reconcile/card-payment"
    try:
        resp = requests.get(url, headers=_headers(), params={'txnRef': txn_ref}, timeout=30)
    except requests.RequestException as exc:
        logger.warning("ZainPay reconcile network error for %s: %s", txn_ref, exc)
        return None

    logger.info("ZainPay reconcile %s — HTTP %s — %s", txn_ref, resp.status_code, resp.text[:400])
    try:
        result = resp.json()
    except ValueError:
        return None

    if str(result.get('code')) != '00':
        return None

    txn_status = (result.get('data') or {}).get('txnStatus', '').lower()
    if txn_status not in ('success', 'failed'):
        return None  # still not definitive — leave it pending for a later retry

    return {'status': txn_status, 'amount': Decimal('0.00'), 'gateway_reference': txn_ref, 'raw_response': result}


def process_payment(payment) -> dict:
    """
    Verify a single pending ApplicationPayment against ZainPay and persist
    all changes (payment + invoice status). Returns
    {'status': 'success'|'pending'|'failed', 'changed': bool}.
    Raises ZainPayError if the ZainPay API call fails.
    Idempotent — calling this on an already-confirmed payment is a no-op.
    """
    from django.utils import timezone as tz

    if payment.status == 'success':
        return {'status': 'success', 'changed': False}

    result = verify_payment(payment.reference)
    new_status = result['status']
    changed = new_status != payment.status

    payment.status = new_status
    payment.gateway_response = result['raw_response']
    if new_status == 'success':
        if not payment.paid_at:
            payment.paid_at = tz.now()
        if not payment.receipt_number:
            from payments.models import generate_receipt_number
            payment.receipt_number = generate_receipt_number()
    payment.save()

    if new_status == 'success' and changed:
        invoice = payment.invoice
        invoice.status = 'paid' if invoice.is_paid else 'partial'
        invoice.save(update_fields=['status'])
        _send_payment_confirmation_email(payment)

    return {'status': new_status, 'changed': changed}


def _send_payment_confirmation_email(payment) -> None:
    """Dispatches on payment kind since ApplicationPayment and
    StudentPayment need different wording — mirrors the dual-purpose
    design this was ported from (glittering/payments/services.py), which
    already split admissions-fee vs school-fee confirmations this way."""
    from hamdaan_cms.emails import send_email
    from payments.models import StudentPayment

    if isinstance(payment, StudentPayment):
        student = payment.invoice.student
        send_email(
            subject=f'{student.full_name} — School Fees Payment Confirmed',
            message=(
                f"Dear {student.full_name},\n\n"
                f"We have received a payment of ₦{payment.amount:,.2f} towards your "
                f"({student.student_id}) school fees for {payment.invoice.session}.\n\n"
                f"Outstanding balance: ₦{payment.invoice.balance:,.2f}\n\n"
                "Hamdaan International College of Health, Science and Technology"
            ),
            to_email=student.user.email,
        )
        return

    application = payment.invoice.application
    send_email(
        subject=f'Application {application.application_number} — Payment Confirmed',
        message=(
            f"Dear {application.applicant.get_full_name() or application.applicant.email},\n\n"
            f"We have received your application fee payment of ₦{payment.amount:,.2f} "
            f"(Application No: {application.application_number}).\n\n"
            "You can now log in to complete your application form.\n\n"
            "Hamdaan International College of Health, Science and Technology"
        ),
        to_email=application.applicant.email,
    )
