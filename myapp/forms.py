from django import forms
from .models import *

class BaseFilterForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Студент"
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Група"
    )
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Дисципліна"
    )
    course = forms.ChoiceField(
        choices=[('', 'Nothing selected')],
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker'}),
        label = "Курс"
    )
    specialty = forms.ModelChoiceField(
        queryset=SpecialtyDepartment.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Спеціальність"
    )
    lesson = forms.ChoiceField(
        choices=[('', 'Ничего не выбрано')],
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label="Вид заняття"
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if departments:
            self.fields['student'].queryset = Student.objects.filter(
                group__specialties__department__in=departments
            ).distinct()

            self.fields['group'].queryset = Group.objects.filter(
                specialties__department__in=departments
            )


            group_names = {group.name for group in self.fields['group'].queryset}
            discipline_ids = set()
            for discipline in Discipline.objects.all():
                discipline_groups = {g.strip() for g in discipline.groups.split(',') if g.strip()}
                if any(group_name in discipline_groups for group_name in group_names):
                    discipline_ids.add(discipline.id)
            self.fields['discipline'].queryset = Discipline.objects.filter(id__in=discipline_ids).distinct()


            years = Group.objects.filter(specialties__department__in=departments).values_list('year', flat=True).distinct()
            self.fields['course'].choices = [(year, year) for year in years]

            # self.fields['specialty'].queryset = Specialty.objects.filter(departments__department__in=departments)
            self.fields['specialty'].queryset = SpecialtyDepartment.objects.filter(
                department__in=departments
            ).select_related('specialty', 'department').distinct()

            # Фильтрация уроков
            lesson_queryset = Lesson_visit.objects.filter(
                group__specialties__department__in=departments
            ).values_list('lesson', flat=True).distinct()
            self.fields['lesson'].choices = [] + [(lesson, lesson) for lesson in
                                                                           lesson_queryset]


        else:
            if fields is None or 'student' in fields:
                self.fields['student'].queryset = Student.objects.all()

            if fields is None or 'group' in fields:
                self.fields['group'].queryset = Group.objects.all()

            if fields is None or 'discipline' in fields:
                self.fields['discipline'].queryset = Discipline.objects.all()

            if fields is None or 'course' in fields:
                years = Group.objects.values_list('year', flat=True).distinct()
                self.fields['course'].choices = [] + [(year, year) for year in years]

            # if fields is None or 'specialty' in fields:
            #     self.fields['specialty'].queryset = Specialty.objects.all()

            if fields is None or 'specialty' in fields:
                self.fields['specialty'].queryset = SpecialtyDepartment.objects.all().select_related('specialty',
                                                                                                     'department')

            if fields is None or 'lesson' in fields:
                lessons = Lesson_visit.objects.values_list('lesson', flat=True).distinct()
                self.fields['lesson'].choices = [] + [(lesson, lesson) for lesson in lessons]


class FolderUploadForm(forms.Form):
    folder = forms.FileField(label="Файл", widget=forms.ClearableFileInput(attrs={'multiple': False}))


class VisitForm(BaseFilterForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label="Студент"
    )

    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=True,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label="Дисципліна"
    )

    lesson = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Вид заняття"
    )

    date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Дата"
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course'], departments=departments, **kwargs)

        for field_name in list(self.fields.keys()):
            if field_name not in ['student', 'discipline', 'date', 'lesson']:
                del self.fields[field_name]


class LessonVisitFilterForm(BaseFilterForm):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Дата від"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Дата до"
    )

    student = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Студент"
    )
    group = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Група"
    )
    discipline = forms.ModelMultipleChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Дисципліна"
    )
    course = forms.MultipleChoiceField(
        choices=[('', 'Нічого не вибрано')],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'}),
        label = "Курс"
    )
    specialty = forms.ModelMultipleChoiceField(
        queryset=SpecialtyDepartment.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Спеціальність"
    )
    lesson = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'}),
        label="Вид заняття"
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course', 'specialty', 'lesson'], departments=departments, **kwargs)


class LessonVisitChartForm(BaseFilterForm):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Дата від"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Дата до"
    )

    student = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Студент"
    )
    group = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Група"
    )
    discipline = forms.ModelMultipleChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Дисципліна"
    )
    course = forms.MultipleChoiceField(
        choices=[('', 'Нічого не вибрано')],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'}),
        label = "Курс"
    )
    specialty = forms.ModelMultipleChoiceField(
        queryset=SpecialtyDepartment.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        label = "Спеціальність"
    )
    lesson = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'}),
        label="Вид заняття"
    )

    CHART_TYPES = [
        ('pie', 'Кругова діаграма'),
        ('bar', 'Стовпчаста діаграма'),
        ('line', 'Лінійна діаграма'),
        ('heatmap', 'Теплова карта'),
    ]
    chart_type = forms.ChoiceField(
        choices=CHART_TYPES,
        required=False,
        label="Тип діаграм",
        widget=forms.Select(attrs={'class': 'selectpicker'})
    )

    DATA_TYPES = [
        ('discipline', 'По дисциплінах'),
        ('group', 'По групах'),
        ('day_of_week', 'По днях тижня'),
    ]
    data_type = forms.ChoiceField(choices=DATA_TYPES,
        required=False,
        label="Тип даних",
        widget=forms.Select(attrs={'class': 'selectpicker'})
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course', 'specialty', 'lesson'], departments=departments, **kwargs)


class LessonVisitPredictorFilterForm(BaseFilterForm):

    student = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    group = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    discipline = forms.ModelMultipleChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    course = forms.MultipleChoiceField(
        choices=[('', 'Nothing selected')],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'})
    )
    specialty = forms.ModelMultipleChoiceField(
        queryset=SpecialtyDepartment.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    lesson = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker'}),
        label="Вид заняття"
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course', 'specialty', 'lesson'], departments=departments, **kwargs)