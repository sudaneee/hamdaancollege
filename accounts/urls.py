from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify/', views.verify_email, name='verify_email'),
    path('verify/resend/', views.resend_code, name='resend_code'),
    path('login/', views.login_view, name='login'),
    path('login/staff/', views.staff_login_view, name='staff_login'),
    path('login/student/', views.student_login_view, name='student_login'),
    path('logout/', views.logout_view, name='logout'),

    # Password reset — Django's built-in views, styled to match the site.
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
