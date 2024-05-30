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


def flush_database(request):
    if request.method == 'POST':
        call_command('flush', interactive=False)  # Вызов команды flush
        return loading_data(request)
    return loading_data(request)


def calendar_view(request):
    form = DateForm()
    visits = None
    selected_date = None

    if request.method == 'POST':
        form = DateForm(request.POST)
        if form.is_valid():
            selected_date = form.cleaned_data['date']
            visits = Lesson_visit.objects.filter(date=selected_date)

    elif request.method == 'GET':
        date = request.GET.get('date', None)
        if date:
            selected_date = date
            visits = Lesson_visit.objects.filter(date=date)
            form = DateForm(initial={'date': date})

    return render(request, 'calendar.html', {'form': form, 'visits': visits, 'selected_date': selected_date})


def delete_visit(request, visit_id):
    if request.method == 'POST':
        visit = Lesson_visit.objects.get(pk=visit_id)
        date = visit.date
        visit.delete()
        # Перенаправляем пользователя обратно на страницу календаря с выбранной датой
        return redirect(reverse('calendar') + f'?date={date if date else ""}')
    return redirect('calendar')


def add_visit(request):
    error_message = None
    if request.method == 'POST':
        form = VisitForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                date = form.cleaned_data['date']
                return redirect(reverse('calendar') + f'?date={date if date else ""}')
            except IntegrityError as e:
                error_message = str(e)
    else:
        date = request.GET.get('date', '')
        form = VisitForm(initial={'date': date})

    return render(request, 'add_visit.html', {'form': form, 'error_message': error_message})


def main(request):
    return render(request, 'base.html')


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


def download_report(request):
    groups = None
    error_message = None
    selected_groups = None
    name = None
    year = None

    if request.method == 'POST':
        form = DisciplineForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            year = form.cleaned_data['year']

            discipline = Discipline.objects.filter(name=name, year=year).first()
            if discipline:
                groups = discipline.groups.split(',') if discipline.groups else []
                selected_groups = request.POST.getlist('groups')
                groups_without_spaces = [group.strip() for group in selected_groups]
                if groups_without_spaces:  # Проверяем, выбраны ли группы
                    file_path = create_excel_template(discipline, groups_without_spaces)
                    download_result = download_file(request, file_path)
                    return download_result
                # else:
                #     error_message = "No groups selected."
            else:
                error_message = "Discipline not found."
        else:
            error_message = "Form is not valid. Please correct the errors."
            messages.error(request, error_message)
    else:
        form = DisciplineForm()

    return render(request, 'download_report.html', {'form': form, 'groups': groups, 'error_message': error_message, 'name': name, 'year': year})



def students_list(request):
    groups = Group.objects.all()
    students = Student.objects.all()
    return render(request, 'students_list.html', {'groups': groups, 'students': students})


def discipline_list(request):
    disciplines = Discipline.objects.all()
    return render(request, 'discipline_list.html', {'disciplines': disciplines})


def visiting_list(request):
    visitings = Lesson_visit.objects.all()
    return render(request, 'visiting_list.html', {'visitings': visitings})


