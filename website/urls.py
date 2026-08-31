from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('programmes/', views.programmes, name='programmes'),
    path('programmes/<slug:slug>/', views.programme_detail, name='programme_detail'),
    path('admissions/', views.admissions, name='admissions'),
    path('departments/', views.departments, name='departments'),
    path('facilities/', views.facilities, name='facilities'),
    path('student-life/', views.student_life, name='student_life'),
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('gallery/', views.gallery, name='gallery'),
    path('careers/', views.careers_list, name='careers_list'),
    path('careers/<slug:slug>/', views.job_detail, name='job_detail'),
    path('contact/', views.contact, name='contact'),
    path('search/', views.search, name='search'),
]
