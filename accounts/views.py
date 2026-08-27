from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.forms import LoginForm, RegisterForm, VerifyCodeForm
from accounts.models import ApplicantProfile, EmailVerification

PENDING_USER_SESSION_KEY = 'pending_verification_user_id'


def _log_in_as(request, user):
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)


def _authenticate_by_identifier(request, identifier, password):
    """Applicant accounts always have username == email (set at
    registration), but staff/admin accounts — createsuperuser, or created
    with a real username via the console — don't necessarily. Try the
    identifier as a username first, then fall back to looking it up as
    an email."""
    user = authenticate(request, username=identifier, password=password)
    if user is None:
        match = User.objects.filter(email__iexact=identifier).first()
        if match:
            user = authenticate(request, username=match.username, password=password)
    return user


def register(request):
    if request.user.is_authenticated:
        return redirect('admissions:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data['email'], email=data['email'], password=data['password1'],
                first_name=data['first_name'], last_name=data['last_name'], is_active=False,
            )
            ApplicantProfile.objects.create(user=user, phone=data['phone'])
            EmailVerification.issue_for(user)
            request.session[PENDING_USER_SESSION_KEY] = user.pk
            messages.success(request, f"We've sent a verification code to {user.email}.")
            return redirect('accounts:verify_email')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request):
    user_id = request.session.get(PENDING_USER_SESSION_KEY)
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        messages.info(request, 'Please register or log in first.')
        return redirect('accounts:register')

    if request.method == 'POST':
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            verification = EmailVerification.objects.filter(user=user, code=code).order_by('-created_at').first()
            if verification and verification.is_valid:
                verification.is_used = True
                verification.save(update_fields=['is_used'])
                user.is_active = True
                user.save(update_fields=['is_active'])
                del request.session[PENDING_USER_SESSION_KEY]
                _log_in_as(request, user)
                messages.success(request, 'Email verified! You can now proceed with your application.')
                return redirect('admissions:dashboard')
            form.add_error('code', 'That code is invalid or has expired. Request a new one below.')
    else:
        form = VerifyCodeForm()

    return render(request, 'accounts/verify_email.html', {'form': form, 'email': user.email})


def resend_code(request):
    user_id = request.session.get(PENDING_USER_SESSION_KEY)
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        return redirect('accounts:register')

    if not EmailVerification.can_resend(user):
        messages.error(request, 'Please wait a moment before requesting another code.')
    else:
        EmailVerification.issue_for(user)
        messages.success(request, f'A new code has been sent to {user.email}.')
    return redirect('accounts:verify_email')


def login_view(request):
    """Applicant Portal login — deliberately separate from the Staff Portal
    (accounts:staff_login): a staff account authenticating correctly here
    still isn't let in, so the two portals never bleed into each other."""
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('admissions:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']
            user = _authenticate_by_identifier(request, identifier, password)

            if user is not None and user.is_staff:
                messages.error(request, 'Staff accounts sign in through the Staff Portal instead.')
            elif user is not None:
                _log_in_as(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(next_url or 'admissions:dashboard')
            else:
                existing = User.objects.filter(
                    Q(username__iexact=identifier) | Q(email__iexact=identifier), is_active=False,
                ).first()
                if existing:
                    request.session[PENDING_USER_SESSION_KEY] = existing.pk
                    messages.info(request, 'This account is not verified yet. Enter the code we sent you.')
                    return redirect('accounts:verify_email')

                messages.error(request, 'Invalid email/username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def staff_login_view(request):
    """Staff Portal login — the one entry point for both the Superadmin
    Console and Django admin (super admins are just staff users with
    is_superuser also set, so there's no third login needed for them)."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_console:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']
            user = _authenticate_by_identifier(request, identifier, password)

            if user is not None and user.is_staff:
                _log_in_as(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(next_url or 'admin_console:home')
            elif user is not None:
                messages.error(request, "That account doesn't have staff portal access.")
            else:
                messages.error(request, 'Invalid email/username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/staff_login.html', {'form': form})


def student_login_view(request):
    """Student Portal login — separate from Applicant/Staff, same rejection
    pattern: authenticates fine but requires a `.student` profile (created
    by the console's "Admit as Student" action on an approved Application)."""
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        return redirect('students:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']
            user = _authenticate_by_identifier(request, identifier, password)

            if user is not None and hasattr(user, 'student'):
                _log_in_as(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(next_url or 'students:dashboard')
            elif user is not None:
                messages.error(request, "That account doesn't have student portal access.")
            else:
                messages.error(request, 'Invalid email/username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/student_login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('website:home')
