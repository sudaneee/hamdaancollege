import random

from django.conf import settings
from django.db import models
from django.utils import timezone

CODE_VALIDITY_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60


class ApplicantProfile(models.Model):
    """
    Everything an applicant account needs beyond what auth.User already
    gives us (email as username, password, is_active as the verified gate).
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applicant_profile')
    phone = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} profile"


def generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


class EmailVerification(models.Model):
    """
    A one-time 6-digit code emailed to confirm account ownership. A user may
    have several rows over time (resends, re-registration) — only the most
    recent unused, unexpired one is ever valid; issuing a new one doesn't
    need to delete old rows, `is_valid` just checks it isn't used/expired.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verifications')
    code = models.CharField(max_length=6, default=generate_code)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.code}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=CODE_VALIDITY_MINUTES)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() <= self.expires_at

    @classmethod
    def issue_for(cls, user):
        """Create (and email) a fresh code for this user."""
        from hamdaan_cms.emails import send_email

        verification = cls.objects.create(user=user)
        send_email(
            subject='Verify your email — Hamdaan International College',
            message=(
                f"Hello {user.get_full_name() or user.email},\n\n"
                f"Your verification code is: {verification.code}\n\n"
                f"This code expires in {CODE_VALIDITY_MINUTES} minutes. If you didn't request this, "
                "you can safely ignore this email.\n\n"
                "Hamdaan International College of Health, Science and Technology"
            ),
            to_email=user.email,
        )
        return verification

    @classmethod
    def can_resend(cls, user) -> bool:
        last = cls.objects.filter(user=user).order_by('-created_at').first()
        if not last:
            return True
        return (timezone.now() - last.created_at).total_seconds() >= RESEND_COOLDOWN_SECONDS


class StaffProfile(models.Model):
    """
    Console role for a staff account. Any is_staff user with no profile
    (or is_superuser=True) is treated as 'full_access' — this preserves
    every existing staff/superuser account's behaviour unchanged; the
    console only restricts a user once they're explicitly assigned a
    narrower role here. See admin_console/permissions.py for the map of
    what each non-full-access role can actually see/do.
    """
    ROLE_CHOICES = [
        ('full_access', 'Full Access (Super Admin)'),
        ('exam_officer', 'Exam Officer'),
        ('registrar', 'Registrar'),
        ('bursar', 'Bursar'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile',
        limit_choices_to={'is_staff': True},
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='full_access')

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_role_display()}"


class Notification(models.Model):
    """
    Generic per-user notification — not tied to the student portal
    specifically, even though that's the first thing to use it, so
    applicants/staff can reuse it later without a new model.
    """
    TYPE_CHOICES = [('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('error', 'Error')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    link = models.CharField(max_length=255, blank=True, help_text="Optional relative URL to link to.")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.message[:40]}"
