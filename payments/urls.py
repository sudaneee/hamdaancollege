from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    path('apply/', views.apply_payment, name='apply_payment'),
    path('apply/pay/', views.initiate_application_payment, name='initiate_application_payment'),
    path('apply/payment/<int:payment_pk>/check/', views.check_application_payment_status, name='check_application_payment_status'),

    # Order matters: <path:session> is greedy (matches slashes too), so the
    # more specific literal-suffixed patterns must be listed first or this
    # would swallow "/pay/" or "/payment/<pk>/check/" into the session
    # string itself instead of matching those routes.
    path('student/payment/<int:payment_pk>/check/', views.check_student_payment_status, name='check_student_payment_status'),
    path('student/<path:session>/pay/', views.initiate_student_payment, name='initiate_student_payment'),
    path('student/<path:session>/', views.student_fee_payment, name='student_fee_payment'),

    path('zainpay/callback/', views.zainpay_callback, name='zainpay_callback'),
]
