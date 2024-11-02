from urllib.parse import urlencode
from django.shortcuts import render, redirect
from .data_loader import load_data_from_excel, load_discipline_from_excel, load_visiting_from_csv
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

    # Инициализация формы
    departments = request.user.departments.all()
    form = DisciplineForm(departments=departments)

    if request.method == 'POST':
        # Обработка первой формы
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

        # Обработка второй формы
        elif 'download_report' in request.POST:
            selected_groups = request.POST.getlist('groups')
            name = request.POST.get('name')  # Получаем name из POST-запроса
            year = request.POST.get('year')  # Получаем year из POST-запроса

            # Проверка на наличие дисциплины и года
            if not name or not year:
                error_message = "Discipline name or year is missing."
            elif selected_groups:
                discipline = Discipline.objects.filter(name=name, year=year).first()  # Получаем дисциплину снова
                if discipline:  # Убедимся, что дисциплина существует
                    groups_without_spaces = [group.strip() for group in selected_groups]
                    file_path = create_excel_template(discipline, groups_without_spaces)  # Передаем discipline
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
                visits = visits.filter(email=student)
        if group:
                visits = visits.filter(group=group)
        if course:
                visits = visits.filter(group__year=course)
        if discipline:
                visits = visits.filter(discipline=discipline)

        if date_from and date_to:
            visits = visits.filter(date__range=(date_from, date_to))
        elif date_from:
            visits = visits.filter(date=date_from)

        # Фильтрация по специальности
        if specialty:
            specialty_groups = Group.objects.filter(specialty=specialty)
            visits = visits.filter(group__in=specialty_groups)

    context = {
        'form': form,
        'visits': visits,
    }
    return render(request, 'filter.html', context)




