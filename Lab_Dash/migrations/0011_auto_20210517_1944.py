# Generated by Django 3.1.3 on 2021-05-17 17:44

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0010_auto_20210517_1446'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 17, 19, 44, 20, 534339), null=True),
        ),
    ]
