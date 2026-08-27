from functools import wraps

from django.shortcuts import redirect


def student_required(view_func):
    """Mirrors accounts' staff/applicant gating — anyone without a
    `.student` profile gets sent to the Student Portal login, never a
    generic 403 (consistent with how the other two portals reject)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'student'):
            return redirect('accounts:student_login')
        return view_func(request, *args, **kwargs)
    return wrapper
