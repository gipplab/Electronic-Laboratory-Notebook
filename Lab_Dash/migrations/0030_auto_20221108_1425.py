# Generated by Django 3.1.3 on 2022-11-08 13:25

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0029_auto_20221102_1154'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2022, 11, 8, 14, 25, 8, 430540), null=True),
        ),
    ]
