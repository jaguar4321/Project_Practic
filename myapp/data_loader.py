import pandas as pd
from django.db import transaction
from .models import *
import csv
import re
from datetime import datetime
import zipfile
from py7zr import SevenZipFile
import os


#  обробка zip_file
def handle_archive(folder, process_function):
    errors = []

    try:
        if not os.path.exists(folder):
            raise FileNotFoundError("File not found")

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
                    errors.append(process_function(file_path))

        elif file_extension.lower() == '.7z':
            with SevenZipFile(folder, 'r') as sz_ref:
                sz_ref.extractall(os.path.dirname(folder))
                names = sz_ref.getnames()

                for filename in names[1:]:
                    file_path = os.path.join(os.path.dirname(folder), filename)
                    errors.append(process_function(file_path))

        else:
            raise ValueError("Unsupported archive format")

    except FileNotFoundError as e:
        errors.append(str(e))

    except zipfile.BadZipFile as e:
        errors.append(f"Error extracting ZIP archive: {str(e)}")

    except Exception as e:
        errors.append(f"Error processing archive: {str(e)}")

    return errors


#  обробка файлу із студентськими даними
def load_data_from_excel(file_path):
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    errors = []
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
                                group_object, _ = Group.objects.get_or_create(name=group_name, year=group_year, specialty=None)
                            else:
                                full_name = row[1]
                                email = str(row[2])
                                if email.endswith('@cs.khpi.edu.ua'):
                                    try:
                                        student = Student.objects.get(email=email)
                                    except Student.DoesNotExist:
                                        student = Student.objects.create(full_name=full_name, group=group_object, email=email)
                                        student.save()
                        except Exception as e:
                            errors.append(f"Error processing data in sheet '{sheet_name}': {str(e)}")
                except Exception as e:
                    errors.append(f"Error reading sheet '{sheet_name}' from Excel file: {str(e)}")
    except Exception as e:
        errors.append(f"Error opening Excel file: {str(e)}")
    xl.close()
    return errors


#  обробка файлу із переліком дисциплін
def load_discipline_from_excel(file_path):
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names

    columns_needed = ['Назва учбової дисципліни', 'Скор', 'Групи', 'Курс']

    disciplines_to_create = {}
    errors = []

    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=5)
            df = df[columns_needed]
            df = df.iloc[1:]
            for index, row in df.iterrows():
                score = str(row['Скор']).strip()
                course = int(row['Курс'])
                score_and_course = (score, course)
                groups = ', '.join(
                    str(g) for g in str(row['Групи']).split(',') if g.strip())

                if score_and_course not in disciplines_to_create:
                    disciplines_to_create[score_and_course] = {
                        'name': row['Назва учбової дисципліни'],
                        'abbrev': score,
                        'groups': groups,
                        'year': course
                    }
                else:
                    existing_groups = set(disciplines_to_create[score_and_course]['groups'].split(', '))
                    new_groups = set(groups.split(', '))
                    all_groups = existing_groups.union(new_groups)
                    disciplines_to_create[score_and_course]['groups'] = ', '.join(all_groups)
        except Exception as e:
            errors.append(str(e))

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
                    if not Discipline.objects.filter(abbrev=discipline_data['abbrev'],
                                                     year=discipline_data['year']).exists():
                        Discipline.objects.create(**discipline_data)
        except IntegrityError as e:
            errors.append(str(e))
    xl.close()
    return errors


#  обробка файлу із відвідуванням дисциплін
def load_visiting_from_csv(filename):
    errors = []

    in_participants_section = False
    attendee_data = []
    try:
        with open(filename, newline='', encoding='utf-16') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')

            for row in reader:
                if row and row[0] == '2. Participants':
                    in_participants_section = True
                    continue

                if in_participants_section and row:
                    if len(row) >= 6 and (row[5] == 'Attendee' or row[5] == 'Presenter'):
                        attendee_data.append(row[4])
    except FileNotFoundError:
        errors.append(f"Неможливо відкрити файл: {filename}")
        return errors
    filename = os.path.basename(filename)
    regex_pattern = r"(\d{8})=([^=]+)=([^=]+)\.csv"
    match = re.match(regex_pattern, filename)
    if match:
        date_str = match.group(1)
        discipline_name = match.group(2)
        lesson = match.group(3)

        date = datetime.strptime(date_str, "%Y%m%d").date()
        discipline = Discipline.objects.filter(abbrev=discipline_name).first()

        if not discipline:
            errors.append(f"Дисципліна з ім'ям '{discipline_name}' не знайдена.")

        for email in attendee_data:
            email = email.lower()
            student = Student.objects.filter(email=email).first()

            if not student:
                errors.append(f"Студент с email '{email}' не знайден.")
                continue

            group = student.group

            existing_visit = Lesson_visit.objects.filter(email=student, date=date, discipline=discipline, lesson=lesson).first()
            if existing_visit is None:
                try:
                    lesson_visit = Lesson_visit(email=student, date=date, discipline=discipline, lesson=lesson)
                    lesson_visit.save()
                except IntegrityError as e:
                    errors.append(str(e))
            else:
                errors.append(f"Запис для {email} на {date} з дисципліни {discipline_name} вже існує.")
    else:
        errors.append("Ім'я файлу не відповідає очікуваному формату.")

    return errors









