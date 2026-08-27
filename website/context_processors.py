from .models import SiteSettings, Statistic


def site_globals(request):
    """Makes site-wide settings available in every template without
    each view having to fetch and pass it manually."""
    return {
        'site_settings': SiteSettings.load(),
        'nav_statistics': Statistic.objects.all()[:3],
    }
