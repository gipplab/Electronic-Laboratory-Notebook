# Generated by Django 3.1.3 on 2023-11-01 04:15

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0045_auto_20231101_0013'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expbase',
            name='Name',
            field=models.TextField(blank=True, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 1, 0, 15, 35, 170931), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 1, 0, 15, 35, 170931), null=True),
        ),
    ]
