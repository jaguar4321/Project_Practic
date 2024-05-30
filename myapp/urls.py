from django.contrib import admin
from django.urls import path, re_path
from . import views



urlpatterns = [
    path('', views.main, name='main'),
    path('loading_data/', views.loading_data, name='loading_data'),
    path('download_report/', views.download_report, name='download_report'),
    path('students_list/', views.students_list, name='students_list'),
    path('discipline_list/', views.discipline_list, name='discipline_list'),
    path('visiting_list/', views.visiting_list, name='visiting_list'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('delete/<int:visit_id>/', views.delete_visit, name='delete_visit'),
    path('add_visit/', views.add_visit, name='add_visit'),
    path('flush_database/', views.flush_database, name='flush_database'),
]