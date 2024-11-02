from django.urls import path, re_path
from . import views



urlpatterns = [
    path('', views.main, name='main'),
    path('loading_data/', views.loading_data, name='loading_data'),
    path('loading_data_user/', views.loading_data_user, name='loading_data_user'),
    path('download_report/', views.download_report, name='download_report'),
    path('students_list/', views.students_list, name='students_list'),
    path('discipline_list/', views.discipline_list, name='discipline_list'),
    path('visiting_list/', views.visiting_list, name='visiting_list'),
    path('delete/<int:visit_id>/', views.delete_visit, name='delete_visit'),
    path('add_visit/', views.add_visit, name='add_visit'),
    path('flush_database/', views.flush_database, name='flush_database'),
    path('lesson-visit-filter/', views.lesson_visit_filter, name='lesson_visit_filter'),
    path('visit-analysis/', views.visit_analysis, name='visit_analysis'),
    path('generate-report/', views.generate_pdf_report, name='generate_pdf_report')
]