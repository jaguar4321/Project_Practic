from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from myapp.models import Department


class CustomUserCreationForm(UserCreationForm):
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=True,
        label="Кафедри",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',  # Добавьте классы Bootstrap
            'placeholder': 'Выберите кафедры',  # Плейсхолдер (можно убрать)
        })
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'departments')
