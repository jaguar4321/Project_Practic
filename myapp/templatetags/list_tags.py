from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    return dictionary.get(key, '-')

@register.filter
def make_key(date, lesson):
    # Обрабатываем date как объект datetime.date или строку
    if isinstance(date, str):
        date_str = date  # Если это уже строка, используем как есть
    else:
        date_str = date.strftime('%Y-%m-%d')  # Если это объект даты, преобразуем в строку
    return f"{date_str}:{lesson}"


@register.filter
def has_lesson(date_lessons, lesson):
    """
    Перевіряє, чи є в date_lessons записи з вказаним lesson.
    Повертає True, якщо є хоча б один відповідний запис, і False, якщо немає.
    """
    lesson = str(lesson)  # Приведення до рядка для типобезпечності
    return any(str(dl['lesson']) == lesson for dl in date_lessons)