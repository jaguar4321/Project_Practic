from django.db import models
from django.db import IntegrityError

class Institute(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва інституту")
    abbrev = models.CharField(max_length=255, verbose_name="Скорочена назва")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Інститут"
        verbose_name_plural = "Інститути"

class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва кафедри")
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='departments',
                                  verbose_name="Інститут")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Кафедра"
        verbose_name_plural = "Кафедри"

class Specialty(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва спеціальності")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Спеціальність"
        verbose_name_plural = "Спеціальності"

class SpecialtyDepartment(models.Model):
    specialty = models.ForeignKey(
        Specialty, on_delete=models.CASCADE, related_name='departments', verbose_name="Спеціальність"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name='specialties', verbose_name="Кафедра"
    )

    class Meta:
        unique_together = ('specialty', 'department')
        verbose_name = "Спеціальність Кафедри"
        verbose_name_plural = "Спеціальності Кафедр"

    def __str__(self):
        return f"{self.specialty} - {self.department}"

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    year = models.CharField(max_length=100)
    specialties = models.ManyToManyField(
        SpecialtyDepartment, blank=True, related_name='groups', verbose_name="Спеціальності")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Група"
        verbose_name_plural = "Групи"

class Discipline(models.Model):
    name = models.CharField(max_length=100)
    abbrev = models.CharField(max_length=100)
    groups = models.CharField(max_length=100)
    year = models.CharField(max_length=100)
    total_time = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Дисципліна"
        verbose_name_plural = "Дисципліни"

class Student(models.Model):
    full_name = models.CharField(max_length=200)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='students')
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенти"

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
                if Lesson_visit.objects.filter(
                        email=self.email,
                        date=self.date,
                        discipline=self.discipline,
                        lesson=self.lesson,
                        group=student.group
                ):
                    raise IntegrityError(
                        "Запис із такою комбінацією студента, дати, дисципліни, виду заняття та групи вже існує."
                    )

        super().save(*args, **kwargs)

    def course(self):
        return self.group.year

    def __str__(self):
        return f"{self.email}"

    class Meta:
        unique_together = ('email', 'date', 'discipline', 'lesson', 'group')
        verbose_name = "Відвідування Заняття"
        verbose_name_plural = "Відвідування Занять"

class LoadingData(models.Model):
    class Meta:
        verbose_name = "Завантаження Даних"
        verbose_name_plural = "Завантаження Даних"