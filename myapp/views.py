from lib2to3.fixes.fix_input import context
from urllib.parse import urlencode
from django.shortcuts import render, redirect
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf.files import pisaFileObject

from .data_loader import load_data_from_excel, load_discipline_from_excel, load_visiting_from_csv, load_specialties_from_excel
from django.contrib import messages
from .forms import *
from .models import *
from django.http import HttpResponse
from .report_excel import create_excel_template
from .loading_unloading import handle_uploaded_folder, download_file
from django.core.management import call_command
from django.urls import reverse
from django.http import QueryDict
from django.contrib.auth.decorators import login_required, user_passes_test
from .charting import *
# from pyppeteer import launch
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import os
from django.conf import settings



import plotly.graph_objects as go
# import json
# from django.db.models import Count, Avg
# import plotly.utils
# from datetime import timedelta
# from django.utils import timezone
# import plotly.express as px
# import plotly.io as pio


@login_required
def flush_database(request):
    if request.method == 'POST':
        call_command('flush', interactive=False)
        return loading_data(request)
    return loading_data(request)


@login_required
def delete_visit(request, visit_id):
    if request.method == 'POST':
        visit = Lesson_visit.objects.get(pk=visit_id)
        visit.delete()

        filter_params = request.GET.urlencode()

        return redirect(reverse('lesson_visit_filter') + f'?{filter_params}')
    return redirect('lesson_visit_filter')


@login_required
def add_visit(request):
    departments = request.user.departments.all()
    error_message = None
    if request.method == 'POST':
        form = VisitForm(request.POST, departments=departments)
        if form.is_valid():
            try:
                lesson_visit = Lesson_visit(
                    email=form.cleaned_data['student'],
                    date=form.cleaned_data['date'],
                    discipline=form.cleaned_data['discipline'],
                    lesson=form.cleaned_data['lesson']
                )
                lesson_visit.save()
                return redirect(f"{reverse('lesson_visit_filter')}?{request.GET.urlencode()}")
            except IntegrityError as e:
                error_message = str(e)
    else:
        initial_data = {
            'student': request.GET.get('student'),
            'date': request.GET.get('date_from'),
            'discipline': request.GET.get('discipline'),
        }


        form = VisitForm(initial=initial_data, departments=departments)

    return render(request, 'add_visit.html', {'form': form, 'error_message': error_message})



# @login_required
def main(request):
    return render(request, 'base.html')


@user_passes_test(lambda u: u.is_superuser)
def loading_data(request):
    error_message = None
    if request.method == 'POST':
        form = FolderUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_function = request.POST.get('upload_function')
            file_or_folder = request.FILES['folder']

            if upload_function == 'load_data_from_excel':
                error_message = handle_uploaded_folder(file_or_folder, load_data_from_excel)
            elif upload_function == 'load_discipline_from_excel':
                error_message = handle_uploaded_folder(file_or_folder, load_discipline_from_excel)
            elif upload_function == 'load_visiting_from_csv':
                error_message = handle_uploaded_folder(file_or_folder, load_visiting_from_csv)
            elif upload_function == 'load_specialties_from_excel':
                error_message = handle_uploaded_folder(file_or_folder, load_specialties_from_excel)

    else:
        form = FolderUploadForm()
    return render(request, 'loading_data.html', {'form': form, 'error_message': error_message})


@login_required
def loading_data_user(request):
    error_message = None
    if request.method == 'POST':
        form = FolderUploadForm(request.POST, request.FILES)
        if form.is_valid():

            file_or_folder = request.FILES['folder']
            error_message = handle_uploaded_folder(file_or_folder, load_visiting_from_csv)

    else:
        form = FolderUploadForm()
    return render(request, 'loading_data_user.html', {'form': form, 'error_message': error_message})


@login_required
def download_report(request):
    error_message = None
    groups = None
    name = None
    year = None

    departments = request.user.departments.all()
    form = DisciplineForm(departments=departments)

    if request.method == 'POST':
        if 'view_groups' in request.POST:
            form = DisciplineForm(request.POST, departments=departments)
            if form.is_valid():
                name = form.cleaned_data['discipline']
                year = form.cleaned_data['course']
                discipline = Discipline.objects.filter(name=name, year=year).first()

                if discipline:
                    groups = discipline.groups.split(',') if discipline.groups else []
                else:
                    error_message = "Discipline not found."
            else:
                error_message = "Form is not valid. Please correct the errors."


        elif 'download_report' in request.POST:
            selected_groups = request.POST.getlist('groups')
            name = request.POST.get('name')
            year = request.POST.get('year')


            if not name or not year:
                error_message = "Discipline name or year is missing."
            elif selected_groups:
                discipline = Discipline.objects.filter(name=name, year=year).first()
                if discipline:
                    groups_without_spaces = [group.strip() for group in selected_groups]
                    file_path = create_excel_template(discipline, groups_without_spaces)
                    return download_file(request, file_path)
                else:
                    error_message = "Discipline not found."
            else:
                error_message = "No groups selected."

    return render(request, 'download_report.html', {
        'form': form,
        'groups': groups,
        'error_message': error_message,
        'name': name,
        'year': year
    })


@login_required
def students_list(request):
    groups = Group.objects.all()
    students = Student.objects.all()
    return render(request, 'students_list.html', {'groups': groups, 'students': students})


@login_required
def discipline_list(request):
    disciplines = Discipline.objects.all()
    return render(request, 'discipline_list.html', {'disciplines': disciplines})


@login_required
def visiting_list(request):
    visitings = Lesson_visit.objects.all()
    return render(request, 'visiting_list.html', {'visitings': visitings})


# Функция для загрузки ресурсов
def fetch_pdf_resources(uri, rel):
    # Если URI не начинается с STATIC_URL
    if uri.find(settings.STATIC_URL) != 0:
        # Путь к шрифту или другому ресурсу, если он не в STATIC_URL
        path = os.path.join(settings.BASE_DIR, 'myapp/static/fonts/DejaVuSans.ttf')
    elif uri.find(settings.MEDIA_URL) != -1:
        # Для файлов в MEDIA_URL
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
    elif uri.find(settings.STATIC_URL) != -1:
        # Для файлов в STATIC_URL
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ''))
    else:
        path = None

    print(path)  # Для отладки
    return path


# Функция для создания PDF отчета
def generate_pdf_report(request, visits):
    # Генерация HTML контента из шаблона
    html_content = render_to_string('pdf_report_template.html', {'visits': visits})

    # Создание PDF из HTML
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="attendance_report.pdf"'
    pisaFileObject.getNamedFile = lambda self: self.uri
    # Используем xhtml2pdf для преобразования HTML в PDF с link_callback для загрузки ресурсов
    pisa_status = pisa.CreatePDF(html_content, dest=response, encoding='UTF-8', fetch_resources=fetch_pdf_resources,
                                 link_callback=fetch_pdf_resources)

    if pisa_status.err:
        return HttpResponse('Ошибка при создании PDF.', status=500)

    return response


@login_required
def lesson_visit_filter(request):
    visits = None
    departments = request.user.departments.all()
    form = LessonVisitFilterForm(request.GET or None, departments=departments)

    if form.is_valid():
        student = form.cleaned_data.get('student')
        group = form.cleaned_data.get('group')
        course = form.cleaned_data.get('course')
        discipline = form.cleaned_data.get('discipline')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        specialty = form.cleaned_data.get('specialty')

        visits = Lesson_visit.objects.all()

        if student:
                visits = visits.filter(email__in=student)
        if group:
                visits = visits.filter(group__in=group)
        if course:
                visits = visits.filter(group__year__in=course)
        if discipline:
                visits = visits.filter(discipline__in=discipline)

        if date_from and date_to:
            visits = visits.filter(date__range=(date_from, date_to))
        elif date_from:
            visits = visits.filter(date=date_from)


        if specialty:
            specialty_groups = Group.objects.filter(specialties__specialty__in=specialty)

            visits = visits.filter(group__in=specialty_groups)

    context = {
        'form': form,
        'visits': visits,
    }

    if 'download_pdf' in request.GET:
        return generate_pdf_report(request, visits)

    return render(request, 'filter.html', context)


# @login_required
# def visit_analysis(request):
#     visits = Lesson_visit.objects.all()
#
#     # 1. Круговая диаграмма для демонстрации общего процента посещений всех занятий
#     total_visits = visits.count()
#     visit_percentage = visits.values('discipline__name').annotate(avg_attendance=Avg('discipline__total_time'))
#     categories = {"Высокая посещаемость": 0, "Средняя посещаемость": 0, "Низкая посещаемость": 0}
#
#     for v in visit_percentage:
#         if v['avg_attendance'] > 90:
#             categories["Высокая посещаемость"] += 1
#         elif 60 <= v['avg_attendance'] <= 90:
#             categories["Средняя посещаемость"] += 1
#         else:
#             categories["Низкая посещаемость"] += 1
#
#     fig1 = go.Figure(data=[go.Pie(labels=list(categories.keys()), values=list(categories.values()))])
#     fig1.update_layout(title='Процент посещаемости всех занятий')
#
#     # 2. Горизонтальная столбчатая диаграмма для сравнения посещаемости по группам
#     visits_by_group = visits.values('group__name').annotate(count=Count('id'))
#     groups = [entry['group__name'] for entry in visits_by_group]
#     group_counts = [entry['count'] for entry in visits_by_group]
#
#     fig2 = go.Figure(data=[go.Bar(name='Посещения', x=group_counts, y=groups, orientation='h')])
#     fig2.update_layout(title='Посещаемость по группам', xaxis_title='Количество посещений', yaxis_title='Группы')
#
#     # 3. Линейный график динамики посещаемости по неделям
#     start_date = timezone.now() - timedelta(weeks=15)
#     visits_over_time = visits.filter(date__gte=start_date).values('date').annotate(count=Count('id')).order_by('date')
#     dates = [entry['date'] for entry in visits_over_time]
#     counts = [entry['count'] for entry in visits_over_time]
#
#     fig3 = go.Figure(data=[go.Scatter(name='Посещения', x=dates, y=counts, mode='lines+markers')])
#     fig3.update_layout(title='Динамика посещаемости по неделям', xaxis_title='Дата', yaxis_title='Количество посещений')
#
#     # 4. Распределение посещаемости по предметам
#     visits_by_discipline = visits.values('discipline__name').annotate(count=Count('id'))
#     disciplines = [entry['discipline__name'] for entry in visits_by_discipline]
#     discipline_counts = [entry['count'] for entry in visits_by_discipline]
#
#     fig4 = go.Figure(data=[go.Bar(name='Посещения', x=disciplines, y=discipline_counts)])
#     fig4.update_layout(title='Распределение посещаемости по предметам', xaxis_title='Дисциплины',
#                        yaxis_title='Количество посещений')
#
#     # 5. Посещаемость по дням недели
#     visits_by_weekday = visits.extra({'weekday': "strftime('%%w', date)"}).values('weekday').annotate(
#         count=Count('id')).order_by('weekday')
#     weekdays = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
#     weekday_counts = [entry['count'] for entry in visits_by_weekday]
#
#     fig5 = go.Figure(data=[go.Bar(name='Посещения', x=weekdays, y=weekday_counts)])
#     fig5.update_layout(title='Посещаемость по дням недели', xaxis_title='День недели',
#                        yaxis_title='Количество посещений')
#
#     # Конвертация графиков в JSON для рендеринга в шаблоне
#     graphJSON1 = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
#     graphJSON2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
#     graphJSON3 = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
#     graphJSON4 = json.dumps(fig4, cls=plotly.utils.PlotlyJSONEncoder)
#     graphJSON5 = json.dumps(fig5, cls=plotly.utils.PlotlyJSONEncoder)
#
#     context = {
#         'graphJSON1': graphJSON1,
#         'graphJSON2': graphJSON2,
#         'graphJSON3': graphJSON3,
#         'graphJSON4': graphJSON4,
#         'graphJSON5': graphJSON5,
#     }
#     return render(request, 'visit_analysis.html', context)


@login_required
def visit_analysis(request):
    chart = None
    visits = None
    departments = request.user.departments.all()
    form = LessonVisitFilterForm(request.GET or None, departments=departments)

    if form.is_valid():
        student = form.cleaned_data.get('student')
        group = form.cleaned_data.get('group')
        course = form.cleaned_data.get('course')
        discipline = form.cleaned_data.get('discipline')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        specialty = form.cleaned_data.get('specialty')

        visits = Lesson_visit.objects.all()

        if student:
            visits = visits.filter(email__in=student)
        if group:
            visits = visits.filter(group__in=group)
        if course:
            visits = visits.filter(group__year__in=course)
        if discipline:
            visits = visits.filter(discipline__in=discipline)

        if date_from and date_to:
            visits = visits.filter(date__range=(date_from, date_to))
        elif date_from:
            visits = visits.filter(date=date_from)

        if specialty:
            specialty_groups = Group.objects.filter(specialties__specialty__in=specialty)

            visits = visits.filter(group__in=specialty_groups)

        # chart = get_attendance_data(visits)
        # chart = group_attendance_bar_chart(visits)
        # chart = attendance_trend_over_semester(visits)
        # chart = attendance_distribution_by_discipline(visits)
        chart = attendance_by_day_of_week(visits)
    context = {
        'form': form,
        'chart': chart
    }
    return render(request, 'visit_analysis.html', context)




