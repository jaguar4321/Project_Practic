# Generated by Django 5.0.4 on 2024-04-14 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discipline',
            name='abbrev',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='discipline',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
