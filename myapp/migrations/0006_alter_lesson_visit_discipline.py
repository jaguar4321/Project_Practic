# Generated by Django 5.0.4 on 2024-04-15 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_alter_discipline_abbrev'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson_visit',
            name='discipline',
            field=models.CharField(max_length=100),
        ),
    ]