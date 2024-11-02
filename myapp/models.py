from django.db import models
from django.db import IntegrityError
# from django.contrib.auth.models import AbstractUser

class Institute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва інституту")
    abbrev = models.CharField(max_length=255, verbose_name="Скорочена назва")

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва кафедри")
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='departments',
                                  verbose_name="Інститут")

    def __str__(self):
        return self.name


class Specialty(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва спеціальності")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='specialties', verbose_name="Кафедра")

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    year = models.CharField(max_length=100)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, related_name='groups',
                                  verbose_name="Спеціальність")

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
        student = self.email
        if student:
            group = student.group
            if group:
                self.group = group

                discipline_groups = [g.strip() for g in self.discipline.groups.split(',')]
                if group.name not in discipline_groups:
                    raise IntegrityError(f"Дисципліна {self.discipline.name} не викладається для цієї групи {group.name}.")
        super().save(*args, **kwargs)

    def course(self):
        return self.group.year

    def __str__(self):
        return self.email

    class Meta:
        unique_together = ('email', 'date', 'discipline', 'lesson')


class LoadingData(models.Model):
    class Meta:
        verbose_name = "Loading Data"
        verbose_name_plural = "Loading Data"








