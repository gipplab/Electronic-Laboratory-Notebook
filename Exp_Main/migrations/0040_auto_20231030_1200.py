# Generated by Django 3.1.3 on 2023-10-30 16:00

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0039_auto_20231030_1142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 0, 24, 519356), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 0, 24, 519356), null=True),
        ),
    ]
