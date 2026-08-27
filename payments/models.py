import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from admissions.models import Application


def generate_invoice_number():
    return f"APP-INV-{timezone.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"


def generate_payment_reference():
    return f"HIC-{uuid.uuid4().hex[:12].upper()}"


def generate_receipt_number():
    return f"RCT-{uuid.uuid4().hex[:8].upper()}"


class ApplicationInvoice(models.Model):
    """
    The application fee, snapshotted at creation time from the applicant's
    AdmissionCycle.fee — never a live lookup, so a later fee change on the
    cycle never alters an invoice already issued.
    """
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=30, unique=True, default=generate_invoice_number, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.invoice_number} — {self.get_status_display()}"

    @property
    def amount_paid(self):
        return self.payments.filter(status='success').aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    @property
    def balance(self):
        return max(self.amount - self.amount_paid, Decimal('0.00'))

    @property
    def is_paid(self):
        return self.amount_paid >= self.amount


def get_or_create_invoice(application):
    """Shared by the dashboard and the payment page — whichever the
    applicant lands on first snapshots the fee from application.cycle.fee;
    the other just picks up the same row via get_or_create."""
    invoice, _ = ApplicationInvoice.objects.get_or_create(
        application=application, defaults={'amount': application.cycle.fee},
    )
    return invoice


class ApplicationPayment(models.Model):
    GATEWAY_CHOICES = [('zainpay', 'ZainPay'), ('manual', 'Manual (Bank Transfer)'), ('waiver', 'Waiver')]
    STATUS_CHOICES = [('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('reversed', 'Reversed')]

    invoice = models.ForeignKey(ApplicationInvoice, on_delete=models.CASCADE, related_name='payments')
    reference = models.CharField(max_length=40, unique=True, default=generate_payment_reference)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES, default='zainpay')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    gateway_reference = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()} (₦{self.amount:,.2f})"


# =========================================================
# School fees (students) — same shape as ApplicationInvoice/
# ApplicationPayment above so payments.zainpay's initiate/verify/
# process_payment work against these unchanged (they're duck-typed
# against .balance/.status/.is_paid, not tied to any one model).
# =========================================================

class StudentInvoice(models.Model):
    STATUS_CHOICES = ApplicationInvoice.STATUS_CHOICES

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='invoices')
    session = models.CharField(max_length=20)
    invoice_number = models.CharField(max_length=30, unique=True, default=generate_invoice_number, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.invoice_number} — {self.get_status_display()}"

    @property
    def amount_paid(self):
        return self.payments.filter(status='success').aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

    @property
    def balance(self):
        return max(self.amount - self.amount_paid, Decimal('0.00'))

    @property
    def is_paid(self):
        return self.amount_paid >= self.amount


def get_or_create_student_invoice(student, session=None):
    """Same lazy-create pattern as get_or_create_invoice() — the fee is
    snapshotted from whatever FeeStructure matches the student's programme
    for the given session (defaults to the student's current session) the
    moment they first need an invoice for it."""
    from students.models import FeeStructure

    session = session or student.session
    invoice = student.invoices.filter(session=session).first()
    if invoice:
        return invoice
    structure = FeeStructure.objects.filter(programme=student.programme, session=session).first()
    amount = structure.amount if structure else Decimal('0.00')
    return StudentInvoice.objects.create(student=student, session=session, amount=amount)


class StudentPayment(models.Model):
    GATEWAY_CHOICES = ApplicationPayment.GATEWAY_CHOICES
    STATUS_CHOICES = ApplicationPayment.STATUS_CHOICES

    invoice = models.ForeignKey(StudentInvoice, on_delete=models.CASCADE, related_name='payments')
    reference = models.CharField(max_length=40, unique=True, default=generate_payment_reference)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES, default='zainpay')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    gateway_reference = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()} (₦{self.amount:,.2f})"
