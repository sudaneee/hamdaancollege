from django.urls import path

from admin_console import views

app_name = 'admin_console'

urlpatterns = [
    path('', views.console_home, name='home'),

    path('applications/', views.applications_list, name='applications_list'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/admit/', views.admit_as_student, name='admit_as_student'),

    path('invoices/', views.invoices_list, name='invoices_list'),

    path('payments/', views.payments_list, name='payments_list'),
    path('payments/<int:pk>/check/', views.payment_check_status, name='payment_check_status'),

    path('students/', views.students_list, name='students_list'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),

    path('student-invoices/', views.student_invoices_list, name='student_invoices_list'),
    path('student-payments/', views.student_payments_list, name='student_payments_list'),
    path('student-payments/<int:pk>/check/', views.student_payment_check_status, name='student_payment_check_status'),

    path('support-tickets/', views.support_tickets_list, name='support_tickets_list'),
    path('support-tickets/<int:pk>/resolve/', views.support_ticket_resolve, name='support_ticket_resolve'),

    path('submissions/', views.submissions_list, name='submissions_list'),

    # Order matters: <path:session> is greedy (matches slashes too), so the
    # more specific literal-suffixed patterns must be listed before the bare
    # gradesheet_detail pattern (see payments/urls.py for the bug this
    # avoids) — download/upload/publish first, plain detail last.
    path('gradesheets/', views.gradesheets_list, name='gradesheets_list'),
    path('gradesheets/<path:session>/<int:course_id>/download/', views.gradesheet_download, name='gradesheet_download'),
    path('gradesheets/<path:session>/<int:course_id>/upload/', views.gradesheet_upload, name='gradesheet_upload'),
    path('gradesheets/<path:session>/<int:course_id>/publish/', views.gradesheet_publish, name='gradesheet_publish'),
    path('gradesheets/<path:session>/<int:course_id>/', views.gradesheet_detail, name='gradesheet_detail'),

    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/toggle-staff/', views.user_toggle_staff, name='user_toggle_staff'),

    path('job-applications/', views.job_applications_list, name='job_applications_list'),
    path('job-applications/<int:pk>/', views.job_application_detail, name='job_application_detail'),

    path('site-settings/', views.site_settings_edit, name='site_settings'),
    path('about-content/', views.about_content_edit, name='about_content'),

    path('<slug:slug>/', views.generic_list, name='list'),
    path('<slug:slug>/add/', views.generic_create, name='create'),
    path('<slug:slug>/<int:pk>/edit/', views.generic_edit, name='edit'),
    path('<slug:slug>/<int:pk>/delete/', views.generic_delete, name='delete'),
]
