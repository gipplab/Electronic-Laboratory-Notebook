# Generated by Django 3.1.3 on 2023-11-01 03:51

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0041_auto_20231030_1247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 31, 23, 51, 37, 441140), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 31, 23, 51, 37, 441140), null=True),
        ),
    ]