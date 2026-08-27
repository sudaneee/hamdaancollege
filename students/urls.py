from django.urls import path

from students import views

app_name = 'students'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('academics/', views.academics, name='academics'),
    path('courses/', views.course_registration_dashboard, name='courses'),
    path('courses/register/', views.course_registration_form, name='course_registration_form'),
    path('courses/<path:session>/', views.course_registration_detail, name='course_registration_detail'),
    path('results/', views.results, name='results'),
    path('results/<path:session>/<str:semester>/', views.result_detail, name='result_detail'),
    path('attendance/', views.attendance, name='attendance'),
    path('timetable/', views.timetable, name='timetable'),
    path('assignments/', views.assignments, name='assignments'),
    path('assignments/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('fees/', views.fees, name='fees'),
    path('fees/<path:session>/', views.fee_detail, name='fee_detail'),
    path('documents/', views.documents, name='documents'),
    path('announcements/', views.announcements, name='announcements'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/<int:pk>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('support/', views.support, name='support'),
]
