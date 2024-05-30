from django import forms
from django_select2.forms import ModelSelect2Widget
from .models import *


class DisciplineForm(forms.Form):
    name = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}))
    year = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super(DisciplineForm, self).__init__(*args, **kwargs)
        self.fields['name'].choices = [(name, name) for name in Discipline.objects.values_list('name', flat=True).distinct()]
        self.fields['year'].choices = [(year, year) for year in Discipline.objects.values_list('year', flat=True).distinct()]


class FolderUploadForm(forms.Form):
    folder = forms.FileField(label="Folder", widget=forms.ClearableFileInput(attrs={'multiple': False}))


class DateForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class VisitForm(forms.ModelForm):
    class Meta:
        model = Lesson_visit
        fields = ['email', 'date', 'discipline', 'lesson']
        widgets = {
            'email': forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
            'discipline': forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
            'lesson': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

