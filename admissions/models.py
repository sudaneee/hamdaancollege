import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from website.models import Programme

GRADE_CHOICES = [
    ('A1', 'A1'), ('B2', 'B2'), ('B3', 'B3'), ('C4', 'C4'), ('C5', 'C5'),
    ('C6', 'C6'), ('D7', 'D7'), ('E8', 'E8'), ('F9', 'F9'),
]
EXAM_BODY_CHOICES = [('WAEC', 'WAEC'), ('NECO', 'NECO'), ('NABTEB', 'NABTEB')]
GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
MARITAL_STATUS_CHOICES = [('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')]
GUARDIAN_RELATIONSHIP_CHOICES = [('Father', 'Father'), ('Mother', 'Mother'), ('Guardian', 'Guardian'), ('Other', 'Other')]
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]


class AdmissionCycle(models.Model):
    """
    One admission "session" (e.g. 2026/2027) that the school opens and
    closes, with its own application fee. Only one cycle is ever active at
    a time — saving one active automatically deactivates any other, so
    "the current cycle" is always unambiguous. Applying is gated on
    `is_open`, not just `is_active`, so an optional opens_at/closes_at
    window can auto-close a cycle without staff having to remember to
    flip the switch.
    """
    session = models.CharField(max_length=20, unique=True, help_text='e.g. 2026/2027')
    is_active = models.BooleanField(default=False, help_text='Only one cycle can be active — activating this one deactivates any other.')
    fee = models.DecimalField(max_digits=10, decimal_places=2, help_text='Application fee for this session, in Naira.')
    opens_at = models.DateTimeField(null=True, blank=True, help_text='Optional — leave blank to rely on the active toggle alone.')
    closes_at = models.DateTimeField(null=True, blank=True, help_text='Optional — leave blank to rely on the active toggle alone.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admission Cycle'
        verbose_name_plural = 'Admission Cycles'

    def __str__(self):
        return f"{self.session} ({'Active' if self.is_active else 'Inactive'})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            AdmissionCycle.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)

    @property
    def is_open(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True

    @classmethod
    def current(cls):
        """The one cycle currently open for applications, or None."""
        for cycle in cls.objects.filter(is_active=True):
            if cycle.is_open:
                return cycle
        return None


def generate_application_number():
    year = timezone.now().year
    for _ in range(10):
        num = ''.join(random.choices(string.digits, k=5))
        candidate = f"HIC-{year}-{num}"
        if not Application.objects.filter(application_number=candidate).exists():
            return candidate
    return f"HIC-{year}-{random.randint(10000, 99999)}"


def application_document_path(instance, filename):
    return f"admissions/{instance.application_number}/{filename}"


class Application(models.Model):
    applicant = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='application')
    cycle = models.ForeignKey(AdmissionCycle, on_delete=models.PROTECT, related_name='applications')
    application_number = models.CharField(max_length=20, unique=True, default=generate_application_number, editable=False)

    # ---- Section A: Personal Information ----
    surname = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, default='Nigerian')
    state_of_origin = models.CharField(max_length=60, blank=True)
    lga = models.CharField(max_length=80, verbose_name='Local Government Area', blank=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    religion = models.CharField(max_length=60, blank=True)
    address = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    alt_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    # ---- Section B: Next of Kin / Guardian Information ----
    guardian_name = models.CharField(max_length=150, blank=True)
    guardian_relationship = models.CharField(max_length=20, choices=GUARDIAN_RELATIONSHIP_CHOICES, blank=True)
    guardian_occupation = models.CharField(max_length=150, blank=True)
    guardian_address = models.CharField(max_length=250, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)

    # ---- Section C: Programme Details ----
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')

    # ---- Section D: Educational Background ----
    previous_school = models.CharField(max_length=200, blank=True)
    qualification_obtained = models.CharField(max_length=100, blank=True)
    qualification_year = models.CharField(max_length=10, blank=True)

    # ---- Section E: O'Level Results (fixed 5 core subjects) ----
    english_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    english_exam_body = models.CharField(max_length=10, choices=EXAM_BODY_CHOICES, blank=True)
    english_year = models.CharField(max_length=10, blank=True)

    maths_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True, verbose_name='Mathematics Grade')
    maths_exam_body = models.CharField(max_length=10, choices=EXAM_BODY_CHOICES, blank=True, verbose_name='Mathematics Examination Body')
    maths_year = models.CharField(max_length=10, blank=True, verbose_name='Mathematics Year')

    chemistry_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    chemistry_exam_body = models.CharField(max_length=10, choices=EXAM_BODY_CHOICES, blank=True)
    chemistry_year = models.CharField(max_length=10, blank=True)

    physics_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    physics_exam_body = models.CharField(max_length=10, choices=EXAM_BODY_CHOICES, blank=True)
    physics_year = models.CharField(max_length=10, blank=True)

    biology_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    biology_exam_body = models.CharField(max_length=10, choices=EXAM_BODY_CHOICES, blank=True)
    biology_year = models.CharField(max_length=10, blank=True)

    # ---- Documents ----
    passport_photo = models.FileField(upload_to=application_document_path, blank=True, null=True)
    olevel_result = models.FileField(upload_to=application_document_path, blank=True, null=True)
    birth_certificate = models.FileField(upload_to=application_document_path, blank=True, null=True)
    identification_document = models.FileField(upload_to=application_document_path, blank=True, null=True)

    # ---- Section F: Declaration ----
    declaration_accepted = models.BooleanField(default=False)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    is_submitted = models.BooleanField(default=False, help_text='False while still being filled in after payment — only True once finally submitted.')
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = ' '.join(p for p in [self.surname, self.first_name] if p) or self.applicant.email
        return f"{self.application_number} — {name}"

    def set_status(self, new_status, note='', user=None):
        """Change status and drop a timeline entry — the one place status
        changes happen, so the console/admin/any future notification code
        never drifts out of sync with the log."""
        self.status = new_status
        self.save(update_fields=['status'])
        self.status_logs.create(stage=new_status, note=note, changed_by=user)

    @property
    def full_name(self):
        return ' '.join(p for p in [self.surname, self.first_name, self.middle_name] if p)

    @property
    def payment_status(self):
        invoice = getattr(self, 'invoice', None)
        return 'paid' if invoice and invoice.is_paid else 'pending'

    STATUS_BADGE_CLASS = {
        'pending': 'badge-warning', 'under_review': 'badge-info',
        'approved': 'badge-success', 'rejected': 'badge-danger',
    }

    @property
    def status_badge_class(self):
        return self.STATUS_BADGE_CLASS.get(self.status, 'badge-muted')

    @property
    def documents_verified(self):
        """No staff verification flag exists yet — presence of the two
        required documents is the best available proxy."""
        return bool(self.passport_photo and self.birth_certificate)

    def get_status_tracker(self):
        """Post-submission review tracker — mirrors the approved static
        prototype's applicant dashboard (Application Started, Submitted,
        Documents Verified, Review, Decision), only ever shown once
        `is_submitted` is True."""
        labels = ['Application Started', 'Submitted', 'Documents Verified', 'Review', 'Decision']
        current_index = 1
        if self.documents_verified:
            current_index = 2
        if self.status == 'under_review':
            current_index = 3
        if self.status in ('approved', 'rejected'):
            current_index = 4

        steps = [
            {'label': label, 'done': i < current_index, 'current': i == current_index}
            for i, label in enumerate(labels)
        ]
        fill_percent = int(current_index / (len(labels) - 1) * 100)
        return {'steps': steps, 'fill_percent': fill_percent}

    def get_progress(self):
        """Lightweight completeness checklist for the dashboard — each
        section is just checked for its key fields being filled in, not a
        separate saved page (the wizard is one combined form)."""
        steps = [
            ('Personal', bool(self.surname and self.first_name and self.phone and self.email)),
            ('Guardian', bool(self.guardian_name and self.guardian_phone)),
            ('Programme', bool(self.programme_id)),
            ('Education', bool(self.previous_school and self.qualification_obtained)),
            ('Documents', bool(self.passport_photo)),
            ('Declaration', self.declaration_accepted),
        ]
        done = sum(1 for _, complete in steps if complete)
        percentage = int(done / len(steps) * 100) if steps else 0
        return {
            'steps': [{'label': label, 'complete': complete} for label, complete in steps],
            'percentage': percentage,
        }


class ApplicationStatusLog(models.Model):
    """One row per status change — the console's audit trail for a review decision."""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_logs')
    stage = models.CharField(max_length=15, choices=STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.application_number} → {self.stage}"


def get_or_create_application(user):
    """The one Application a verified applicant account ever has — created
    lazily against whichever AdmissionCycle is currently open, the moment
    they first land on the dashboard (not a separate forced step)."""
    application = getattr(user, 'application', None)
    if application:
        return application
    cycle = AdmissionCycle.current()
    if not cycle:
        return None
    return Application.objects.create(applicant=user, cycle=cycle, email=user.email)
