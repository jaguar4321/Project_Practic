import plotly.express as px
from django.db.models import Count
from django.db.models.functions import TruncWeek, ExtractWeekDay

from .models import *
import plotly.graph_objects as go

def chart_visits_bar_chart(qs):
    pass

# круговая діаграма для демонстрації загального відсотка відвідуваності всіх дисциплин.
def get_attendance_data(visits):
    # Словарь для хранения категорий посещаемости
    categories = {
        "Высокая посещаемость": 0,
        "Средняя посещаемость": 0,
        "Низкая посещаемость": 0,
    }

    # Группировка посещений по дисциплинам
    disciplines = visits.values('discipline').distinct()

    for discipline in disciplines:
        discipline_id = discipline['discipline']

        # Получаем дисциплину и общее количество занятий
        discipline_obj = Discipline.objects.get(id=discipline_id)
        total_lessons = discipline_obj.total_time / 1.5
        print(total_lessons)

        # Количество посещений для конкретной дисциплины
        discipline_visits_count = visits.filter(discipline=discipline_obj).count()
        print(discipline_visits_count)

        # Вычисляем процент посещаемости
        attendance_percentage = (discipline_visits_count / total_lessons) * 100 if total_lessons > 0 else 0
        print(attendance_percentage)

        # Классифицируем по категориям
        if attendance_percentage > 90:
            categories["Высокая посещаемость"] += 1
        elif 60 <= attendance_percentage <= 90:
            categories["Средняя посещаемость"] += 1
        else:
            categories["Низкая посещаемость"] += 1

    # Подготовка данных для графика
    labels = list(categories.keys())
    values = list(categories.values())

    # Построение круговой диаграммы
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
    fig.update_layout(
        title="Общий процент посещаемости дисциплин",
        showlegend=True,
        font=dict(size=14)
    )

    # Преобразуем график в HTML
    chart_html = fig.to_html(full_html=False)

    return chart_html


# порівняння відвідуваності в різних академічних групах
def group_attendance_bar_chart(visits):
    # Словари для хранения названий групп и их процента посещаемости
    group_attendance = {}

    # Группировка посещений по группам
    groups = visits.values('group').distinct()

    for group in groups:
        group_id = group['group']

        # Получаем название группы
        group_obj = Group.objects.get(id=group_id)
        group_name = group_obj.name

        # Определяем количество посещений и общее количество уроков
        total_lessons = Lesson_visit.objects.filter(group=group_obj).count()
        visits_count = visits.filter(group=group_obj).count()

        # Рассчитываем процент посещаемости для каждой группы
        attendance_percentage = (visits_count / total_lessons) * 100 if total_lessons > 0 else 0
        group_attendance[group_name] = attendance_percentage

    # Подготовка данных для графика
    labels = list(group_attendance.keys())  # Названия групп
    values = list(group_attendance.values())  # Проценты посещаемости

    # Построение горизонтальной столбчатой диаграммы
    fig = go.Figure(data=[go.Bar(x=values, y=labels, orientation='h')])
    fig.update_layout(
        title="Сравнение посещаемости в различных группах",
        xaxis_title="Процент посещаемости",
        yaxis_title="Группа",
        showlegend=False,
        font=dict(size=14)
    )

    # Преобразуем график в HTML
    chart_html = fig.to_html(full_html=False)

    return chart_html



# Динаміка відвідуваності протягом семестру
def attendance_trend_over_semester(visits):
    # Предполагается, что `visits` содержит данные о посещениях с полем даты
    # Группируем данные по неделям или месяцам
    visits_by_week = visits.annotate(week=TruncWeek('date')).values('week').annotate(count=Count('id')).order_by('week')

    # Подготовка данных для графика
    weeks = [visit['week'] for visit in visits_by_week]
    attendance_counts = [visit['count'] for visit in visits_by_week]

    # Построение линейного графика
    fig = go.Figure(go.Scatter(x=weeks, y=attendance_counts, mode='lines+markers'))
    fig.update_layout(
        title="Динамика посещаемости в течение семестра",
        xaxis_title="Неделя",
        yaxis_title="Количество посещений",
        font=dict(size=14)
    )
    return fig.to_html(full_html=False)


# ля показу рівня відвідуваності з окремих предметів
def attendance_distribution_by_discipline(visits):
    # Группируем данные по дисциплинам и считаем посещения
    attendance_by_discipline = visits.values('discipline__name').annotate(count=Count('id')).order_by('-count')

    disciplines = [entry['discipline__name'] for entry in attendance_by_discipline]
    attendance_counts = [entry['count'] for entry in attendance_by_discipline]

    # Построение столбчатого графика
    fig = go.Figure(go.Bar(x=disciplines, y=attendance_counts, orientation='v'))
    fig.update_layout(
        title="Распределение посещаемости по предметам",
        xaxis_title="Предмет",
        yaxis_title="Количество посещений",
        font=dict(size=14)
    )
    return fig.to_html(full_html=False)




# теплова карта для демонстрації, у які дні тижня спостерігається найвища та найнижча відвідуваність
def attendance_by_day_of_week(visits):
    # Получаем день недели для каждого посещения
    visits_by_day = visits.annotate(day=ExtractWeekDay('date')).values('day').annotate(count=Count('id')).order_by(
        'day')

    # Подготовка данных для тепловой карты
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    day_counts = [0] * 7
    for visit in visits_by_day:
        day_counts[visit['day'] - 1] = visit['count']  # Заполняем значения в соответствии с днем недели

    # Создание тепловой карты (сделаем массив 2D, чтобы соответствовать формату `imshow`)
    fig = px.imshow([day_counts], labels=dict(x="День недели", color="Посещения"), x=days, y=["Посещаемость"])
    fig.update_layout(
        title="Посещаемость по дням недели",
        font=dict(size=14)
    )
    return fig.to_html(full_html=False)

