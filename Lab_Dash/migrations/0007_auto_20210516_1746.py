# Generated by Django 3.1.3 on 2021-05-16 15:46

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0006_auto_20210516_1744'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 17, 46, 0, 817859), null=True),
        ),
    ]