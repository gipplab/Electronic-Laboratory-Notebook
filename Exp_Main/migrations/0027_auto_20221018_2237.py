# Generated by Django 3.1.3 on 2022-10-18 20:37

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0026_auto_20221003_2105'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2022, 10, 18, 22, 37, 18, 374620), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2022, 10, 18, 22, 37, 18, 374630), null=True),
        ),
    ]
