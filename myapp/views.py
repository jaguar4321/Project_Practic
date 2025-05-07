from lib2to3.fixes.fix_input import context
from urllib.parse import urlencode

import logging
from django.shortcuts import render, redirect
from django.db.models import Max
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
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import os
from django.conf import settings
from .attendance_predictor import *

logger = logging.getLogger(__name__)

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
    errors = None
    success_message = None
    if request.method == 'POST':
        form = FolderUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_function = request.POST.get('upload_function')
            file_or_folder = request.FILES['folder']

            if upload_function == 'load_data_from_excel':
                errors = handle_uploaded_folder(file_or_folder, load_data_from_excel)
            elif upload_function == 'load_discipline_from_excel':
                errors = handle_uploaded_folder(file_or_folder, load_discipline_from_excel)
            elif upload_function == 'load_visiting_from_csv':
                errors = handle_uploaded_folder(file_or_folder, load_visiting_from_csv)
            elif upload_function == 'load_specialties_from_excel':
                errors = handle_uploaded_folder(file_or_folder, load_specialties_from_excel)
            if not errors or not any(len(value) > 0 for value in errors.values()):
                success_message = "Файл успішно оброблено!"
            # Видаляємо дублікати наприкінці
            for category in errors:
                # Перетворюємо список на множину (set), щоб видалити дублікати, і назад у список
                errors[category] = list(set(errors[category]))

    else:
        form = FolderUploadForm()

    return render(request, 'loading_data.html', {
        'form': form,
        'errors': errors,
        'success_message': success_message
    })


def loading_data_user(request):
    errors = None
    success_message = None
    if request.method == 'POST':
        form = FolderUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_or_folder = request.FILES['folder']
            errors = handle_uploaded_folder(file_or_folder, load_visiting_from_csv)
            if not errors or not any(len(value) > 0 for value in errors.values()):
                success_message = "Файл успішно оброблено!"
            # Видаляємо дублікати наприкінці
            for category in errors:
                # Перетворюємо список на множину (set), щоб видалити дублікати, і назад у список
                errors[category] = list(set(errors[category]))
    else:
        form = FolderUploadForm()

    return render(request, 'loading_data_user.html', {
        'form': form,
        'errors': errors,
        'success_message': success_message
    })




@login_required
def students_list(request):
    departments = request.user.departments.all()
    if departments:
        # Фильтруем группы по кафедрам пользователя
        groups = Group.objects.filter(specialties__department__in=departments).distinct()
        # Фильтруем студентов по группам, связанным с кафедрами
        students = Student.objects.filter(group__specialties__department__in=departments).distinct()
    else:
        # Если кафедр нет, возвращаем все группы и студентов
        groups = Group.objects.all()
        students = Student.objects.all()

    return render(request, 'students_list.html', {'groups': groups, 'students': students})


@login_required
def discipline_list(request):
    departments = request.user.departments.all()
    if departments:
        # Получаем группы, связанные с кафедрами пользователя
        group_names = Group.objects.filter(
            specialties__department__in=departments
        ).values_list('name', flat=True).distinct()

        # Фильтруем дисциплины, которые связаны с этими группами
        discipline_ids = set()
        for discipline in Discipline.objects.all():
            discipline_groups = {g.strip() for g in discipline.groups.split(',') if g.strip()}
            if any(group_name in discipline_groups for group_name in group_names):
                discipline_ids.add(discipline.id)
        disciplines = Discipline.objects.filter(id__in=discipline_ids).distinct()
    else:
        # Если кафедр нет, возвращаем все дисциплины
        disciplines = Discipline.objects.all()

    return render(request, 'discipline_list.html', {'disciplines': disciplines})



def fetch_pdf_resources(uri, rel):
    """Функция для загрузки статических ресурсов"""
    print(f"Запрошен URI: {uri}")  # Отладка

    # Если URI начинается с STATIC_URL
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ''))
    # Если URI начинается с MEDIA_URL
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
    # Для шрифта по умолчанию
    else:
        path = os.path.join(settings.BASE_DIR, 'myapp/static/fonts/DejaVuSans.ttf')

    # Проверяем, существует ли файл
    if os.path.isfile(path):
        print(f"Найден файл: {path}")
    else:
        print(f"Файл не найден: {path}")
        path = None  # Возвращаем None, если файл не найден

    return path

def generate_pdf_report(request, visits, selected_student=None):
    # Подготавливаем данные
    discipline_ids = visits.values('discipline').distinct()
    disciplines = Discipline.objects.filter(id__in=[d['discipline'] for d in discipline_ids])

    disciplines_data = []
    for discipline in disciplines:
        lessons = visits.filter(discipline=discipline).values_list('lesson', flat=True).distinct()
        group_ids = visits.filter(discipline=discipline).values('group').distinct()
        groups = Group.objects.filter(id__in=[g['group'] for g in group_ids])
        group_list = []
        for group in groups:
            date_lessons = visits.filter(
                discipline=discipline, group=group
            ).values('date', 'lesson').distinct().order_by('date', 'lesson')

            # Якщо обрано студентів, використовуємо лише їх
            if selected_student is not None and selected_student.exists():
                students = selected_student.filter(group=group)
            else:
                students = Student.objects.filter(group=group).order_by('full_name')

            # Фільтруємо студентів, які мають відвідування
            students_data = []
            for student in students:
                student_visits = visits.filter(email=student, discipline=discipline, group=group)
                if not student_visits.exists():
                    continue  # Пропускаємо студентів без відвідувань

                visit_marks = {}
                for dl in date_lessons:
                    date_key = dl['date']
                    lesson_key = dl['lesson']
                    date_str = date_key.strftime('%Y-%m-%d') if hasattr(date_key, 'strftime') else date_key
                    key = f"{date_str}:{lesson_key}"
                    has_visit = student_visits.filter(date=date_key, lesson=lesson_key).exists()
                    visit_marks[key] = '+' if has_visit else '-'
                students_data.append({
                    'full_name': student.full_name,
                    'visit_marks': visit_marks
                })

            if students_data:  # Додаємо групу лише якщо є студенти з відвідуваннями
                group_list.append({
                    'id': group.id,
                    'name': group.name,
                    'discipline_id': discipline.id,
                    'date_lessons': date_lessons,
                    'students': students_data
                })

        # Додаємо дисципліну лише якщо є групи з даними
        if group_list:
            disciplines_data.append({
                'discipline': discipline,
                'lessons': lessons,
                'groups': group_list
            })

    # Рендерим шаблон
    context = {
        'disciplines_data': disciplines_data,
        'visits': visits
    }
    html_content = render_to_string('pdf_report_template.html', context)

    # Создание PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="attendance_report.pdf"'

    # Настройка pisaFileObject для корректной обработки путей
    pisaFileObject.getNamedFile = lambda self: self.uri

    # Используем xhtml2pdf для преобразования HTML в PDF
    pisa_status = pisa.CreatePDF(
        html_content,
        dest=response,
        encoding='UTF-8',
        link_callback=fetch_pdf_resources,
        fetch_resources=fetch_pdf_resources
    )

    if pisa_status.err:
        return HttpResponse('Помилка при створенні PDF.', status=500)

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
        lesson = form.cleaned_data.get('lesson')

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
            specialty_groups = Group.objects.filter(specialties__in=specialty)

            visits = visits.filter(group__in=specialty_groups)

        if lesson:
            visits = visits.filter(lesson__in=lesson)

        visits_without_sort = visits
        visits = visits.order_by('group__name', 'discipline__name', '-date')

    context = {
        'form': form,
        'visits': visits,
    }

    if 'download_pdf' in request.GET:
        return generate_pdf_report(request, visits_without_sort, selected_student=student)

    if 'download_excel' in request.GET:
        file_path = create_excel_template(visits_without_sort, selected_student=student)
        return download_file(request, file_path)

    return render(request, 'filter.html', context)


@login_required
def visit_analysis(request):
    chart = None
    visits = None
    departments = request.user.departments.all()
    form = LessonVisitChartForm(request.GET or None, departments=departments)

    if form.is_valid():
        student = form.cleaned_data.get('student')
        group = form.cleaned_data.get('group')
        course = form.cleaned_data.get('course')
        discipline = form.cleaned_data.get('discipline')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        specialty = form.cleaned_data.get('specialty')
        lesson = form.cleaned_data.get('lesson')
        chart_type = form.cleaned_data.get('chart_type')
        data_type = form.cleaned_data.get('data_type')

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
            specialty_groups = Group.objects.filter(specialties__in=specialty)

            visits = visits.filter(group__in=specialty_groups)

        if lesson:
            visits = visits.filter(lesson__in=lesson)


        chart = generate_chart(visits, chart_type, data_type)

    context = {
        'form': form,
        'chart': chart
    }
    return render(request, 'visit_analysis.html', context)


@login_required
def attendance_predictor(request):
    visits = None
    predictions = []
    departments = request.user.departments.all()

    form = LessonVisitPredictorFilterForm(request.GET or None, departments=departments)

    if form.is_valid():
        student = form.cleaned_data.get('student')
        group = form.cleaned_data.get('group')
        course = form.cleaned_data.get('course')
        discipline = form.cleaned_data.get('discipline')
        specialty = form.cleaned_data.get('specialty')
        lesson = form.cleaned_data.get('lesson')

        visits = Lesson_visit.objects.all()

        # Применение фильтров
        if student:
            visits = visits.filter(email__in=student)
        else:
            if group:
                visits = visits.filter(group__in=group)
            if course:
                visits = visits.filter(group__year__in=course)
            if discipline:
                visits = visits.filter(discipline__in=discipline)
            if specialty:
                specialty_groups = Group.objects.filter(specialties__in=specialty)
                visits = visits.filter(group__in=specialty_groups)
            if lesson:
                visits = visits.filter(lesson__in=lesson)

        # Вызов функции прогнозирования
        predictions = predict_attendance(visits)

    context = {
        'form': form,
        'visits': visits,
        'predictions': predictions
    }
    return render(request, 'attendance_predictor.html', context)