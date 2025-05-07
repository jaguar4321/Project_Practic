import plotly.express as px
import plotly.graph_objects as go
from django.db.models import Count
from django.db.models.functions import TruncWeek, ExtractWeekDay
from .models import *
from django.utils import timezone


def generate_chart(visits, chart_type, data_type):
    """
    Генерує діаграму на основі типу діаграми та типу даних.
    :param visits: QuerySet з даними відвідувань
    :param chart_type: Тип діаграми ('pie', 'bar', 'line', 'heatmap')
    :param data_type: Тип даних ('discipline', 'group', 'day_of_week')
    :return: HTML-код діаграми
    """
    if not visits.exists():
        return "<p>Немає даних для відображення.</p>"

    # Загальні налаштування для всіх діаграм
    fig_layout = {
        'font': dict(size=14),
        'showlegend': True
    }

    # 1. Відвідуваність по дисциплінах
    if data_type == 'discipline':
        attendance_data = visits.values('discipline__name').annotate(count=Count('id')).order_by('-count')
        labels = [entry['discipline__name'] for entry in attendance_data]
        values = [entry['count'] for entry in attendance_data]
        title = "Відвідуваність за дисциплінами"

        if chart_type == 'pie':
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
            fig.update_layout(title=title, **fig_layout)
        elif chart_type == 'bar':
            fig = go.Figure(data=[go.Bar(x=labels, y=values)])
            fig.update_layout(title=title, xaxis_title="Дисципліна", yaxis_title="Кількість відвідувань", **fig_layout)
        elif chart_type == 'line':
            fig = go.Figure(data=[go.Scatter(x=labels, y=values, mode='lines+markers')])
            fig.update_layout(title=title, xaxis_title="Дисципліна", yaxis_title="Кількість відвідувань", **fig_layout)
        else:  # heatmap не має сенсу для дисципліни
            return "<p>Теплова карта недоступна для даних по дисциплінах.</p>"

    # 2. Відвідуваність по групах
    elif data_type == 'group':
        group_data = {}
        groups = visits.values('group').distinct()
        for group in groups:
            group_id = group['group']
            group_obj = Group.objects.get(id=group_id)
            group_name = group_obj.name
            total_lessons = Lesson_visit.objects.filter(group=group_obj).count()
            visits_count = visits.filter(group=group_obj).count()
            attendance_percentage = (visits_count / total_lessons) * 100 if total_lessons > 0 else 0
            group_data[group_name] = attendance_percentage
        labels = list(group_data.keys())
        values = list(group_data.values())
        title = "Відвідуваність за групами"

        if chart_type == 'pie':
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
            fig.update_layout(title=title, **fig_layout)
        elif chart_type == 'bar':
            fig = go.Figure(data=[go.Bar(x=labels, y=values)])
            fig.update_layout(title=title, xaxis_title="Група", yaxis_title="Відсоток відвідувань", **fig_layout)
        elif chart_type == 'line':
            fig = go.Figure(data=[go.Scatter(x=labels, y=values, mode='lines+markers')])
            fig.update_layout(title=title, xaxis_title="Група", yaxis_title="Відсоток відвідувань", **fig_layout)
        else:  # heatmap не має сенсу для груп
            return "<p>Теплова карта недоступна для даних по групах.</p>"

    # 3. Відвідуваність по днях тижня
    elif data_type == 'day_of_week':
        # Отримуємо відвідування з днями тижня та датами
        visits_by_day = visits.annotate(day=ExtractWeekDay('date')).values('day', 'date').annotate(
            count=Count('id')).order_by('day')

        # Список днів тижня (1 = неділя, 2 = понеділок, ..., 7 = субота)
        days = ['Неділя', 'Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П’ятниця', 'Субота']
        day_counts = [0] * 7
        day_dates = [[] for _ in range(7)]  # Список для зберігання дат для кожного дня тижня

        # Збираємо дати для кожного дня тижня
        for visit in visits_by_day:
            day_index = visit['day'] - 1  # Перетворюємо 1–7 у 0–6
            day_counts[day_index] = visit['count']
            # Форматуємо дату як рядок
            date_str = visit['date'].strftime('%Y-%m-%d')
            if date_str not in day_dates[day_index]:
                day_dates[day_index].append(date_str)

        labels = days
        values = day_counts
        title = "Відвідуваність за днями тижня"

        # Формуємо вспливаючі підказки
        hover_texts = [f"Дати: {', '.join(dates) if dates else 'Немає дат'}" for dates in day_dates]

        if chart_type == 'pie':
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                customdata=hover_texts,
                hovertemplate="%{label}<br>Відвідувань: %{value}<br>%{customdata}<extra></extra>"
            )])
            fig.update_layout(title=title, **fig_layout)

        elif chart_type == 'bar':
            fig = go.Figure(data=[go.Bar(
                x=labels,
                y=values,
                customdata=hover_texts,
                hovertemplate="%{x}<br>Відвідувань: %{y}<br>%{customdata}<extra></extra>"
            )])
            fig.update_layout(title=title, xaxis_title="День тижня", yaxis_title="Кількість відвідувань", **fig_layout)

        elif chart_type == 'line':
            fig = go.Figure(data=[go.Scatter(
                x=labels,
                y=values,
                mode='lines+markers',
                customdata=hover_texts,
                hovertemplate="%{x}<br>Відвідувань: %{y}<br>%{customdata}<extra></extra>"
            )])
            fig.update_layout(title=title, xaxis_title="День тижня", yaxis_title="Кількість відвідувань", **fig_layout)

        elif chart_type == 'heatmap':
            # Для теплової карти додаємо дати у вспливаючу підказку
            fig = px.imshow(
                [day_counts],
                labels=dict(x="День тижня", color="Відвідування"),
                x=days,
                y=["Відвідуваність"],
                text_auto=True
            )
            fig.update_traces(
                customdata=[hover_texts],
                hovertemplate="%{x}<br>Відвідувань: %{z}<br>%{customdata}<extra></extra>"
            )
            fig.update_layout(title=title, **fig_layout)

        else:
            return "<p>Невірний тип діаграми.</p>"

    else:
        return "<p>Невірний тип даних.</p>"

    return fig.to_html(full_html=False)