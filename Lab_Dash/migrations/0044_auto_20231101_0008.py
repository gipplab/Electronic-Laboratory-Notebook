# Generated by Django 3.1.3 on 2023-11-01 04:08

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0043_auto_20231031_2355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 1, 0, 8, 15, 265810), null=True),
        ),
    ]
