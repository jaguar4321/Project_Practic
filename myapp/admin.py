from django.contrib import admin
from django.urls import path
from .models import *
from .views import loading_data

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'year')
    search_fields = ('name',)


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbrev', 'groups', 'year', 'total_time')
    search_fields = ('name', 'abbrev')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'group', 'email')
    search_fields = ('full_name', 'email')


@admin.register(Lesson_visit)
class LessonVisitAdmin(admin.ModelAdmin):
    list_display = ('email', 'date', 'discipline', 'lesson', 'group')
    search_fields = ('email__full_name', 'discipline__name')
    list_filter = ('date', 'discipline', 'group')


@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'institute',)
    list_filter = ('institute',)
    search_fields = ('name',)


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SpecialtyDepartment)
class SpecialtyDepartmentAdmin(admin.ModelAdmin):
    list_display = ('specialty', 'department')
    search_fields = ('specialty__name', 'department__name')


class LoadingDataAdmin(admin.ModelAdmin):
    change_list_template = "admin/loading_data_admin.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('loading-data/', self.admin_site.admin_view(loading_data), name='loading_data'),
        ]
        return custom_urls + urls

admin.site.register(LoadingData, LoadingDataAdmin)
