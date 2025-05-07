import pandas as pd
from django.db import transaction
from .models import *
import csv
import re
from datetime import datetime
import zipfile
from py7zr import SevenZipFile
import os


def handle_archive(folder, process_function):
    errors = {
        'file_errors': [],
        'discipline_errors': [],
        'student_errors': [],
        'visit_errors': [],
        'format_errors': [],
        'archive_errors': []
    }
    try:
        if not os.path.exists(folder):
            raise FileNotFoundError("Файл не знайдено")

        _, file_extension = os.path.splitext(folder)

        if file_extension.lower() == '.zip':
            with zipfile.ZipFile(folder, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    # Указываем кодировку, которая будет использоваться при извлечении файлов
                    file_info.filename = file_info.filename.encode('cp437').decode('cp866')
                    zip_ref.extract(file_info, os.path.dirname(folder))
                for file_info in zip_ref.infolist():
                    filename = file_info.filename
                    file_path = os.path.join(os.path.dirname(folder), filename)
                    file_errors = process_function(file_path)
                    for key, value in file_errors.items():
                        errors[key].extend(value)

        elif file_extension.lower() == '.7z':
            with SevenZipFile(folder, 'r') as sz_ref:
                sz_ref.extractall(os.path.dirname(folder))
                names = sz_ref.getnames()
                for filename in names[1:]:
                    file_path = os.path.join(os.path.dirname(folder), filename)
                    file_errors = process_function(file_path)  # Отримуємо словник від load_visiting_from_csv
                    # Об'єднуємо помилки
                    for key, value in file_errors.items():
                        errors[key].extend(value)

        else:
            print("ValueError")
            raise ValueError("Непідтримуваний формат архіву")

    except FileNotFoundError as e:
        errors['archive_errors'].append(str(e))
    except zipfile.BadZipFile as e:
        errors['archive_errors'].append(f"Помилка розпакування ZIP-архіву: {str(e)}")
    except Exception as e:
        errors['archive_errors'].append(f"Помилка обробки архіву: {str(e)}")
    return errors


#  обробка файлу із студентськими даними
def load_data_from_excel(file_path):
    errors = {
        'file_errors': [],
        'sheet_errors': [],
        'data_errors': [],
        'student_errors': []
    }

    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
    except Exception as e:
        errors['file_errors'].append(f"Помилка відкриття Excel файлу: {str(e)}")
        return errors

    try:
        with transaction.atomic():
            for sheet_name in sheet_names:
                try:
                    data = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)
                    data = data.iloc[1:]

                    for index, row in data.iterrows():
                        try:
                            if not row[0].isdigit():
                                group_name, group_year = row[0].split(' - курс ')
                                group_object, _ = Group.objects.get_or_create(name=group_name, year=group_year)
                            else:
                                full_name = row[1]
                                email = str(row[2]).strip().lower()
                                if email.endswith('khpi.edu.ua'):
                                    student, created = Student.objects.get_or_create(
                                        email=email,
                                        defaults={'full_name': full_name, 'group': group_object})
                                else:
                                    errors['student_errors'].append(f"Невірний формат email для студента '{full_name}': {email}")
                        except Exception as e:
                            errors['data_errors'].append(f"Помилка обробки даних у рядку {index + 2} аркуша '{sheet_name}': {str(e)}")
                except Exception as e:
                    errors['sheet_errors'].append(f"Помилка читання аркуша '{sheet_name}' з Excel файлу: {str(e)}")
    except Exception as e:
        errors['file_errors'].append(f"Помилка транзакції при обробці файлу: {str(e)}")

    xl.close()
    return errors


#  обробка файлу із переліком дисциплін
def load_discipline_from_excel(file_path):
    errors = {
        'file_errors': [],
        'sheet_errors': [],
        'column_errors': [],
        'data_errors': [],
        'discipline_errors': []
    }

    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
    except Exception as e:
        errors['file_errors'].append(f"Помилка відкриття Excel файлу: {str(e)}")
        return errors

    columns_needed = [
        'Назва учбової дисципліни',
        'Скор',
        'Групи',
        'Курс',
    ]

    disciplines_to_create = {}

    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=[5, 6])
            second_level_columns = df.columns.get_level_values(1)
            df.columns = df.columns.get_level_values(0)

            missing_columns = [col for col in columns_needed if col not in df.columns]
            if missing_columns:
                errors['column_errors'].append(f"Відсутні стовпці в аркуші '{sheet_name}': {missing_columns}")
                continue

            for index, row in df.iterrows():
                try:
                    score = str(row['Скор']).strip()
                    course = int(row['Курс'])
                    groups = ', '.join(str(g) for g in str(row['Групи']).split(',') if g.strip())
                    total = row[second_level_columns == 'Всього'].values[0]

                    score_and_course = (score, course)
                    if score_and_course not in disciplines_to_create:
                        disciplines_to_create[score_and_course] = {
                            'name': row['Назва учбової дисципліни'],
                            'abbrev': score,
                            'groups': groups,
                            'year': course,
                            'total_time': total
                        }
                    else:
                        existing_groups = set(disciplines_to_create[score_and_course]['groups'].split(', '))
                        new_groups = set(groups.split(', '))
                        all_groups = existing_groups.union(new_groups)
                        disciplines_to_create[score_and_course]['groups'] = ', '.join(all_groups)
                except Exception as e:
                    errors['data_errors'].append(f"Помилка обробки рядка {index + 7} аркуша '{sheet_name}': {str(e)}")
        except Exception as e:
            errors['sheet_errors'].append(f"Помилка читання аркуша '{sheet_name}' з Excel файлу: {str(e)}")

    for score_and_course, discipline_data in disciplines_to_create.items():
        try:
            existing_disciplines = Discipline.objects.filter(abbrev=score_and_course[0], year=score_and_course[1])
            if existing_disciplines.exists():
                existing_discipline = existing_disciplines.first()
                existing_groups = set(existing_discipline.groups.split(', '))
                new_groups = set(discipline_data['groups'].split(', '))
                all_groups = existing_groups.union(new_groups)
                existing_discipline.groups = ', '.join(all_groups)
                existing_discipline.save()
            else:
                if discipline_data['abbrev'] != 'асп':
                    if not Discipline.objects.filter(abbrev=discipline_data['abbrev'], year=discipline_data['year']).exists():
                        Discipline.objects.create(**discipline_data)
        except IntegrityError as e:
            errors['discipline_errors'].append(f"Помилка створення/оновлення дисципліни '{discipline_data['name']}': {str(e)}")

    xl.close()
    return errors




 # обробка файлу із переліком відвідування
def load_visiting_from_csv(filename):
    errors = {
        'file_errors': [],
        'discipline_errors': [],
        'student_errors': [],
        'visit_errors': [],
        'format_errors': []
    }

    in_participants_section = False
    attendee_data = []
    date_str = None
    try:
        with open(filename, newline='', encoding='utf-16') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')

            for row in reader:
                if row and row[0] == '2. Participants':
                    in_participants_section = True
                    continue

                if in_participants_section and row:
                    if len(row) >= 6 and (row[5] == 'Attendee' or row[5] == 'Presenter'):
                        attendee_data.append((row[4], row[1]))  # Store email and First Join date
                        if date_str is None and row[1]:
                            # Extract date from First Join (e.g., "3/04/24, 12:30:35 PM")
                            try:
                                date_part = row[1].split(',')[0].strip()  # Get "3/18/24"
                                date_str = datetime.strptime(date_part, "%m/%d/%y").date()
                            except ValueError:
                                errors['format_errors'].append(f"Невірний формат дати у стовпці First Join: {row[1]}")
    except FileNotFoundError:
        errors['file_errors'].append(f"Неможливо відкрити файл: {filename}")
        return errors

    # Extract discipline_name and lesson from filename
    filename = os.path.basename(filename)
    regex_pattern = r"(?:[^=]+?=)?([^=]+)=([^=]+)\.csv"
    match = re.match(regex_pattern, filename)
    if not match:
        errors['format_errors'].append("Ім'я файлу не відповідає очікуваному формату.")
        return errors

    discipline_name = match.group(1)
    lesson = match.group(2) if match.group(2) else ""  # Use empty string if lesson is not provided
    discipline = Discipline.objects.filter(abbrev=discipline_name).first()

    if not discipline:
        errors['discipline_errors'].append(f"Дисципліна з ім'ям '{discipline_name}' не знайдена.")
        return errors

    if not date_str:
        errors['format_errors'].append("Не вдалося визначити дату з даних CSV.")
        return errors

    for email, _ in attendee_data:
        email = email.lower()
        student = Student.objects.filter(email=email).first()
        if not student:
            errors['student_errors'].append(f"Студент з email '{email}' не знайдений.")
            continue

        try:
            lesson_visit, created = Lesson_visit.objects.get_or_create(
                email=student,
                date=date_str,
                discipline=discipline,
                lesson=lesson,
                defaults={'email': student, 'date': date_str, 'discipline': discipline, 'lesson': lesson}
            )
        except IntegrityError as e:
            errors['visit_errors'].append(
                f"Помилка збереження відвідування для {email}: {str(e)}"
            )

    return errors





#  обробка файлу із переліком спеціальностей, кафедр, відповідно групам
# def load_specialties_from_excel(file_path):
#
#     df = pd.read_excel(file_path)
#     print(df)
#     # Проверяем, содержит ли DataFrame "Група"
#     if 'Група' not in df.columns or df['Група'].str.contains('Бакалаврат').any() is False:
#         print("Группа 'Бакалаврат' не найдена в файле Excel.")
#         return
#
#     institute_name = df['Інститут'].dropna().iloc[0] if not df['Інститут'].dropna().empty else None
#     if institute_name:
#         institute, _ = Institute.objects.get_or_create(name=institute_name)  # Создаем или получаем объект Institute
#         print(f"Загружается информация для института: {institute_name}")
#     else:
#         print("Не найдено значение для 'Інститут' в файле.")
#         return
#
#
#     # Начинаем транзакцию для целостности данных
#     with transaction.atomic():
#         for index, row in df.iterrows():
#             group_name = row['Група']
#
#             # Пропускаем строки с "Бакалаврат" и пустые строки
#             if group_name == 'Бакалаврат' or pd.isnull(group_name):
#                 continue
#
#             specialty_name = row['Спеціальність']
#             department_name = row['Кафедра']
#
#
#             # Находим первую 'x' и извлекаем префикс
#             x_index = group_name.find('x')
#             prefix = group_name[:x_index-1]  # Все символы до первой 'x'
#
#             # Считаем количество цифр в group_name
#             length_required = sum(1 for char in group_name if char.isdigit() or char == 'х')
#
#             # Получаем или создаём специальность
#             specialty, _ = Specialty.objects.get_or_create(name=specialty_name)
#
#             # Получаем или создаём кафедру
#             department, _ = Department.objects.get_or_create(name=department_name, institute=institute)
#             # Ищем группы, которые начинаются с извлеченного префикса
#             matching_groups = Group.objects.filter(name__startswith=prefix)
#             if matching_groups:
#                 for group in matching_groups:
#                     # Проверяем, совпадает ли количество цифр с требуемым и начинается ли название с prefix
#                     if sum(1 for char in group.name if char.isdigit()) == length_required and group.name.startswith(prefix):
#                         # Добавляем специальность к группе
#                         group.specialties.add(
#                             SpecialtyDepartment.objects.get_or_create(specialty=specialty, department=department)[0])
#                         print(f"Добавлена специальность '{specialty_name}' в группу '{group.name}'.")
#
#     print("Специальности загружены успешно.")


#  обробка файлу із переліком спеціальностей, кафедр, відповідно групам
def load_specialties_from_excel(file_path):
    errors = {
        'file_errors': [],
        'column_errors': [],
        'institute_errors': [],
        'data_errors': [],
        'specialty_errors': []
    }

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        errors['file_errors'].append(f"Помилка відкриття Excel файлу: {str(e)}")
        return errors

    if 'Група' not in df.columns or df['Група'].str.contains('Бакалаврат').any() is False:
        errors['column_errors'].append("Відсутній стовпець 'Група' або група 'Бакалаврат' не знайдена.")
        return errors

    institute_name = df['Інститут'].dropna().iloc[0] if not df['Інститут'].dropna().empty else None
    if not institute_name:
        errors['institute_errors'].append("Не знайдено значення для 'Інститут' у файлі.")
        return errors

    try:
        institute, _ = Institute.objects.get_or_create(name=institute_name)
    except Exception as e:
        errors['institute_errors'].append(f"Помилка створення/отримання інституту '{institute_name}': {str(e)}")
        return errors

    try:
        with transaction.atomic():
            for index, row in df.iterrows():
                group_name = row['Група']
                if group_name == 'Бакалаврат' or pd.isnull(group_name):
                    continue

                try:
                    specialty_name = row['Спеціальність']
                    department_name = row['Кафедра']
                    x_index = group_name.find('x')
                    prefix = group_name[:x_index-1]
                    length_required = sum(1 for char in group_name if char.isdigit() or char == 'х')

                    specialty, _ = Specialty.objects.get_or_create(name=specialty_name)
                    department, _ = Department.objects.get_or_create(name=department_name, institute=institute)

                    matching_groups = Group.objects.filter(name__startswith=prefix)
                    if matching_groups:
                        for group in matching_groups:
                            if sum(1 for char in group.name if char.isdigit()) == length_required and group.name.startswith(prefix):
                                group.specialties.add(
                                    SpecialtyDepartment.objects.get_or_create(specialty=specialty, department=department)[0])
                    else:
                        errors['data_errors'].append(f"Групи з префіксом '{prefix}' не знайдено для спеціальності '{specialty_name}'.")
                except Exception as e:
                    errors['specialty_errors'].append(f"Помилка обробки рядка {index + 2} для спеціальності '{specialty_name}': {str(e)}")
    except Exception as e:
        errors['file_errors'].append(f"Помилка транзакції при обробці файлу: {str(e)}")
    print(errors)
    return errors





