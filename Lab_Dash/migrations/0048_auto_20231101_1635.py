# Generated by Django 3.1.3 on 2023-11-01 20:35

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0047_auto_20231101_1055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 1, 16, 35, 39, 787579), null=True),
        ),
    ]
