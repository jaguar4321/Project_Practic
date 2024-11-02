from django import forms
from .models import *


class BaseFilterForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )
    course = forms.ChoiceField(
        choices=[('', 'Nothing selected')],
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker'})
    )
    specialty = forms.ModelChoiceField(
        queryset=Specialty.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
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

            self.fields['specialty'].queryset = Specialty.objects.filter(departments__department__in=departments)


        else:
            if fields is None or 'student' in fields:
                self.fields['student'].queryset = Student.objects.all()

            if fields is None or 'group' in fields:
                self.fields['group'].queryset = Group.objects.all()

            if fields is None or 'discipline' in fields:
                self.fields['discipline'].queryset = Discipline.objects.all()

            if fields is None or 'course' in fields:
                years = Group.objects.values_list('year', flat=True).distinct()
                self.fields['course'].choices = [('', 'Nothing selected')] + [(year, year) for year in years]

            if fields is None or 'specialty' in fields:
                self.fields['specialty'].queryset = Specialty.objects.all()


class DisciplineForm(BaseFilterForm):
    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course'], departments=departments, **kwargs)

        for field_name in list(self.fields.keys()):
            if field_name not in ['discipline', 'course']:
                del self.fields[field_name]


class FolderUploadForm(forms.Form):
    folder = forms.FileField(label="Файл", widget=forms.ClearableFileInput(attrs={'multiple': False}))


class VisitForm(BaseFilterForm):
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    lesson = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
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
        label="Date From"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date To"
    )

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
        queryset=Specialty.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true'})
    )

    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        super().__init__(*args, fields=['student', 'group', 'discipline', 'course', 'specialty'], departments=departments, **kwargs)