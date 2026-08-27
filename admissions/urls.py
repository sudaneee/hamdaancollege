from django.urls import path

from admissions import views

app_name = 'admissions'

urlpatterns = [
    path('apply/', views.apply, name='apply'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('apply/form/', views.apply_form, name='apply_form'),
    path('apply/success/<str:application_number>/', views.apply_success, name='apply_success'),
]
