import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from admissions.models import Application
from website.models import Programme

DAY_CHOICES = [('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
               ('Thursday', 'Thursday'), ('Friday', 'Friday')]
SEMESTER_CHOICES = [('First', 'First Semester'), ('Second', 'Second Semester')]
STATUS_CHOICES = [('Active', 'Active'), ('Suspended', 'Suspended'), ('Graduated', 'Graduated'), ('Withdrawn', 'Withdrawn')]
GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]

# Standard grading scale — score -> (grade, grade_point out of 4.0, remark).
# Applied automatically in Result.save() so staff only ever type a score.
GRADE_SCALE = [
    (70, 'A', Decimal('4.0'), 'Excellent'),
    (60, 'B', Decimal('3.0'), 'Very Good'),
    (50, 'C', Decimal('2.0'), 'Good'),
    (45, 'D', Decimal('1.0'), 'Pass'),
    (0, 'F', Decimal('0.0'), 'Fail'),
]


def grade_for_score(score):
    for threshold, grade, point, remark in GRADE_SCALE:
        if score >= threshold:
            return grade, point, remark
    return 'F', Decimal('0.0'), 'Fail'


def generate_student_id(programme):
    year = timezone.now().year
    category = programme.category if programme else 'ND'
    for _ in range(10):
        seq = ''.join(random.choices(string.digits, k=4))
        candidate = f"HIC/{category}/{year}/{seq}"
        if not Student.objects.filter(student_id=candidate).exists():
            return candidate
    return f"HIC/{category}/{year}/{random.randint(1000, 9999)}"


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student')
    application = models.OneToOneField(Application, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_record')
    student_id = models.CharField(max_length=30, unique=True, editable=False)

    surname = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=250, blank=True)
    state = models.CharField(max_length=60, blank=True)
    lga = models.CharField(max_length=80, blank=True)

    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, related_name='students')
    level = models.CharField(max_length=30, blank=True, default='Year 1', help_text="e.g. Year 1, ND II")
    session = models.CharField(max_length=20, help_text="Current academic session, e.g. 2026/2027")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active')
    admission_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_id} — {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = generate_student_id(self.programme)
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return ' '.join(p for p in [self.surname, self.first_name, self.middle_name] if p) or self.user.email

    @property
    def results_current_session(self):
        """Published results only — a Draft result (awaiting Exam Officer
        review) never counts toward anything a student can see or that
        feeds their GPA."""
        return self.results.filter(session=self.session, is_published=True)

    def _gpa_for(self, qs):
        total_units = sum(r.course.units for r in qs)
        if not total_units:
            return Decimal('0.00')
        total_points = sum(r.course.units * r.grade_point for r in qs)
        return (total_points / total_units).quantize(Decimal('0.01'))

    @property
    def gpa(self):
        """Current session's GPA — computed from Result, never stored."""
        return self._gpa_for(self.results_current_session.select_related('course'))

    @property
    def cgpa(self):
        """Cumulative GPA across every published session on record."""
        return self._gpa_for(self.results.filter(is_published=True).select_related('course').all())

    def results_for(self, session, semester=None):
        """Published results for one session, optionally narrowed to one
        semester — the per-session/semester breakdown shown on the Results
        detail page. Never includes drafts still awaiting publish."""
        qs = self.results.filter(session=session, is_published=True)
        if semester:
            qs = qs.filter(semester=semester)
        return qs.select_related('course')

    def gpa_for(self, session, semester=None):
        """GPA for a specific session (optionally just one semester)."""
        return self._gpa_for(self.results_for(session, semester))

    @property
    def attendance_percentage(self):
        records = self.attendance_records.filter(session=self.session)
        total = records.count()
        if not total:
            return 100
        present = records.filter(status='Present').count()
        return round(present / total * 100)

    @property
    def current_invoice(self):
        """The fee invoice for the student's current session, if generated
        yet (payments.get_or_create_student_invoice creates it lazily)."""
        return self.invoices.filter(session=self.session).first()

    @property
    def total_fees(self):
        invoice = self.current_invoice
        return invoice.amount if invoice else Decimal('0.00')

    @property
    def paid_fees(self):
        invoice = self.current_invoice
        return invoice.amount_paid if invoice else Decimal('0.00')

    @property
    def outstanding_fees(self):
        invoice = self.current_invoice
        return invoice.balance if invoice else Decimal('0.00')


class Course(models.Model):
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    units = models.PositiveIntegerField(default=2)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='First')
    level = models.CharField(max_length=30, blank=True, help_text="Must match a student's Level exactly, e.g. ND I, ND II.")
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='courses')
    lecturer_name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.title}"


class CourseRegistration(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='registrations')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registrations')
    session = models.CharField(max_length=20)

    class Meta:
        ordering = ['course__code']
        unique_together = ('student', 'course', 'session')

    def __str__(self):
        return f"{self.student.student_id} — {self.course.code} ({self.session})"


# Continuous Assessment / Exam split — the standard 30:70 weighting. Kept as
# module-level constants (not per-course config, which doesn't exist yet) so
# the gradesheet template/validation and the model's own bounds agree.
MAX_CA_SCORE = 30
MAX_EXAM_SCORE = 70


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='results')
    ca_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=f"Out of {MAX_CA_SCORE}.")
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=f"Out of {MAX_EXAM_SCORE}.")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False, help_text="ca_score + exam_score — computed in save().")
    grade = models.CharField(max_length=2, blank=True, editable=False)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, default=0, editable=False)
    remark = models.CharField(max_length=20, blank=True, editable=False)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='First')
    session = models.CharField(max_length=20)
    # Draft until an Exam Officer explicitly publishes it — students never see
    # a result before that, however it was entered (gradesheet upload or a
    # one-off console edit). Publishing again after an edit is a no-op; there
    # is deliberately no separate "unpublish" step.
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-session', 'course__code']
        unique_together = ('student', 'course', 'session')

    def __str__(self):
        return f"{self.student.student_id} — {self.course.code}: {self.grade}"

    def save(self, *args, **kwargs):
        self.score = self.ca_score + self.exam_score
        self.grade, self.grade_point, self.remark = grade_for_score(float(self.score))
        super().save(*args, **kwargs)


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [('Present', 'Present'), ('Absent', 'Absent')]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    session = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['-date']
        unique_together = ('student', 'course', 'date')

    def __str__(self):
        return f"{self.student.student_id} — {self.course.code} — {self.date} — {self.status}"

    def save(self, *args, **kwargs):
        if not self.session:
            self.session = self.student.session
        super().save(*args, **kwargs)


class TimetableEntry(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='timetable_entries')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='timetable_entries')
    lecturer_name = models.CharField(max_length=100, blank=True)
    venue = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.programme} — {self.day} {self.start_time} — {self.course}"


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.title} ({self.course.code})"


class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='assignment_submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student.student_id} — {self.assignment.title}"


class Announcement(models.Model):
    AUDIENCE_CHOICES = [('All', 'Everyone'), ('Students', 'Students Only'), ('Staff', 'Staff Only')]

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='All')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SupportTicket(models.Model):
    SUBJECT_CHOICES = [
        ('Fees & Payments', 'Fees & Payments'), ('Results & Grades', 'Results & Grades'),
        ('Course Registration', 'Course Registration'), ('Technical Issue', 'Technical Issue'), ('Other', 'Other'),
    ]
    STATUS_CHOICES = [('Open', 'Open'), ('Resolved', 'Resolved')]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES, default='Other')
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.student_id} — {self.subject}"


class FeeStructure(models.Model):
    """One per (programme, session) — a container for the FeeStructureItem
    rows that actually carry the breakdown. `amount` is deliberately not a
    stored field: it's the sum of the fixed-amount items, so it can never
    drift out of sync with the breakdown a student is shown (same
    computed-not-stored philosophy as Student.gpa/cgpa)."""
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='fee_structures')
    session = models.CharField(max_length=20)

    class Meta:
        ordering = ['-session']
        unique_together = ('programme', 'session')

    def __str__(self):
        return f"{self.programme} — {self.session} (₦{self.amount:,.2f})"

    @property
    def amount(self):
        """Total billable amount — the sum of every fixed-price item.
        Variable items (Hostel, Uniforms, "as applicable" charges, etc.)
        are shown to the student for transparency but never charged."""
        total = self.items.filter(amount__isnull=False).aggregate(total=models.Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def fixed_items(self):
        return self.items.filter(amount__isnull=False)

    @property
    def variable_items(self):
        return self.items.filter(amount__isnull=True)


class FeeStructureItem(models.Model):
    """One line of a fee breakdown, e.g. 'Tuition/School Fees — ₦65,000'.
    Leave `amount` blank for a variable charge (Hostel, Uniforms, "as
    applicable" items) — it's shown with `note` instead ('To Be
    Announced') and never counted in FeeStructure.amount."""
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(
        max_length=50, blank=True,
        help_text="Optional group heading shown above this row, e.g. 'First Semester', 'Second Semester'.",
    )
    label = models.CharField(max_length=100, help_text="e.g. Tuition/School Fees")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Leave blank for a variable charge (shown via the Note field instead, e.g. 'To Be Announced').",
    )
    note = models.CharField(
        max_length=50, blank=True,
        help_text="Shown instead of an amount when Amount is left blank, e.g. 'To Be Announced' or 'As Applicable'.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.label} — {self.fee_structure}"


class AcademicSession(models.Model):
    """
    Admin's on/off switch for course registration, per session — several
    can be open at once (e.g. continuing students on 2026/2027 alongside a
    deferred cohort still finishing 2025/2026), so unlike AdmissionCycle
    there's no "only one active" enforcement here.

    `name` must match a Student's `session` field exactly — that's what
    ties a student to whichever row governs their own registration window.
    """
    name = models.CharField(max_length=20, unique=True, help_text="e.g. 2026/2027 — must match Student.session exactly.")
    registration_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return f"{self.name} — {'Registration Open' if self.registration_open else 'Registration Closed'}"
