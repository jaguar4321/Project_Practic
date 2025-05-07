from .models import Lesson_visit, Student, Group, Discipline
from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
import numpy as np
from collections import Counter

def predict_attendance(visits):
    predictions = []

    if not visits.exists():
        return predictions

    # Группировка посещений по студенту, дисциплине и типу занятия
    grouped_visits = visits.values('email', 'discipline', 'lesson').distinct()

    for visit in grouped_visits:
        student_id = visit['email']
        discipline_id = visit['discipline']
        lesson_type = visit['lesson']

        # Получение объектов студента и дисциплины
        student_obj = Student.objects.get(id=student_id)
        discipline_obj = Discipline.objects.get(id=discipline_id)

        # Получение всех посещений для студента, дисциплины и типа занятия
        student_visits = Lesson_visit.objects.filter(
            email=student_obj,
            discipline=discipline_obj,
            lesson=lesson_type
        )

        # Получение всех дат занятий для дисциплины, типа занятия и группы
        group_lesson_dates = Lesson_visit.objects.filter(
            discipline=discipline_obj,
            lesson=lesson_type,
            group=student_obj.group
        ).values('date').distinct().order_by('date')

        # Подсчёт общего количества занятий
        total_lessons = group_lesson_dates.count()

        # Подсчёт посещённых занятий
        attended_lessons = student_visits.count()

        # Расчёт доли посещений
        attendance_rate = attended_lessons / total_lessons if total_lessons > 0 else 0

        # Формирование данных для ML
        X = []
        y = []
        student_visit_dates = student_visits.values_list('date', flat=True)

        # Для каждой даты занятия проверяем, было ли посещение
        for lesson_date in group_lesson_dates:
            date = lesson_date['date']
            X.append([attendance_rate])  # Признак: доля посещений
            if date in student_visit_dates:
                y.append(1)  # Посещение
            else:
                y.append(0)  # Пропуск

        # Преобразование в numpy массивы
        X = np.array(X)
        y = np.array(y)

        # Обучение модели логистической регрессии
        if len(np.unique(y)) > 1 and len(y) >= 2:  # Проверка наличия двух классов и достаточного количества данных
            model = LogisticRegression()
            model.fit(X, y)

            # Прогноз вероятностей
            next_prob = model.predict_proba([[attendance_rate]])[0][1]  # Вероятность посещения следующего занятия
            next_next_prob = next_prob * 0.95  # Немного меньшая вероятность для после следующего
        else:
            # Если недостаточно данных для ML, используем долю посещений как вероятность
            next_prob = attendance_rate
            next_next_prob = next_prob * 0.95 if next_prob > 0 else 0

        # Убедимся, что вероятности в диапазоне [0, 1]
        next_prob = min(max(next_prob, 0.0), 1.0)
        next_next_prob = min(max(next_next_prob, 0.0), 1.0)

        # Получение последней даты и оценка следующих дат
        if student_visits.exists():
            last_date = student_visits.order_by('-date').first().date

            # Анализ интервалов между занятиями
            lesson_dates = [d['date'] for d in group_lesson_dates]
            if len(lesson_dates) >= 2:
                # Вычисляем интервалы между занятиями
                intervals = [(lesson_dates[i + 1] - lesson_dates[i]).days for i in range(len(lesson_dates) - 1)]
                # Находим наиболее частый интервал (моду)
                most_common_interval = Counter(intervals).most_common(1)
                interval = most_common_interval[0][0] if most_common_interval else 7
                interval = max(1, interval)  # Гарантируем, что интервал минимум 1 день
            else:
                interval = 7  # Если недостаточно данных, используем 7 дней

            next_date = last_date + timedelta(days=interval)
            next_next_date = next_date + timedelta(days=interval)

            predictions.append({
                'student': student_obj.full_name,
                'group': student_obj.group.name,
                'discipline': discipline_obj.name,
                'lesson': lesson_type,
                'last_date': last_date,
                'next_date': next_date,
                'next_prob': round(next_prob * 100, 1),
                'next_next_date': next_next_date,
                'next_next_prob': round(next_next_prob * 100, 1)
            })

    return predictions