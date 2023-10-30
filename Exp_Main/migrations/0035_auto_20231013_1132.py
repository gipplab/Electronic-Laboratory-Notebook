# Generated by Django 3.1.3 on 2023-10-13 15:32

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0034_auto_20231013_1109'),
    ]

    operations = [
        migrations.AddField(
            model_name='grv',
            name='Plate_speed_mm_s',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 13, 11, 31, 57, 488929), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 13, 11, 31, 57, 489396), null=True),
        ),
    ]