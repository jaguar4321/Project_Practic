from django.db import models
from django.db import IntegrityError

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    year = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Discipline(models.Model):
    name = models.CharField(max_length=100)
    abbrev = models.CharField(max_length=100)
    groups = models.CharField(max_length=100)
    year = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Student(models.Model):
    full_name = models.CharField(max_length=200)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='students')
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.full_name


class Lesson_visit(models.Model):
    email = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='visiting')
    date = models.DateField()
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, related_name='visiting')
    lesson = models.CharField(max_length=100)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='visiting', default=None)

    def save(self, *args, **kwargs):
        # Поиск студента по его email
        student = self.email
        if student:
            # Получение группы студента
            group = student.group
            if group:
                self.group = group  # Установка найденной группы в поле group

                discipline_groups = [g.strip() for g in self.discipline.groups.split(',')]
                if group.name not in discipline_groups:
                    raise IntegrityError(f"Группа {group.name} не указана для дисциплины {self.discipline.name}.")
        super().save(*args, **kwargs)

    def course(self):
        return self.group.year

    def __str__(self):
        return self.email

    class Meta:
        unique_together = ('email', 'date', 'discipline', 'lesson')

