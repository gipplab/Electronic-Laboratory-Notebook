# Generated by Django 3.1.3 on 2023-11-21 20:22

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0050_auto_20231121_1515'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 21, 15, 22, 32, 646669), null=True),
        ),
    ]
