from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin's own login screen is intercepted (this pattern wins
    # over admin.site.urls' own 'login/' below, since Django resolves URLs
    # in order) and sent to the Staff Portal login instead — Django admin
    # and the Superadmin Console share one staff login, separate from the
    # Applicant/Student Portals. `next` survives in the query string so
    # post-login redirect still lands back here.
    path('django-admin/login/', RedirectView.as_view(pattern_name='accounts:staff_login', query_string=True)),
    path('django-admin/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('accounts/', include('accounts.urls')),
    path('payments/', include('payments.urls')),
    path('student/', include('students.urls')),
    path('console/', include('admin_console.urls')),
    path('', include('admissions.urls')),
    path('', include('website.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
