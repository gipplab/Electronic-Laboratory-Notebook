# Generated by Django 3.1.3 on 2023-10-30 16:47

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0040_auto_20231030_1200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 47, 56, 53842), null=True),
        ),
    ]
