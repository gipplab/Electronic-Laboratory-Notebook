# Generated by Django 3.1.3 on 2023-10-13 15:32

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0034_auto_20231013_1109'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 13, 11, 31, 57, 462358), null=True),
        ),
    ]