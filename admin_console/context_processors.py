from admin_console import permissions


def console_role(request):
    """Makes the current staff user's console role/visibility available in
    every console template (mainly the sidebar in base.html) without every
    view having to compute and pass it manually."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}
    role = permissions.get_role(user)
    profile = getattr(user, 'staff_profile', None)
    return {
        'is_full_access': role == permissions.FULL_ACCESS,
        'console_visible_slugs': permissions.visible_slugs(user),
        'console_visible_dedicated': permissions.visible_dedicated(user),
        'console_role_label': profile.get_role_display() if profile else 'Super Admin',
    }
