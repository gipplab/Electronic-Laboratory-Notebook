# Generated by Django 3.1.3 on 2021-05-29 10:29

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Dash', '0013_auto_20210529_1225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sel',
            name='Start_datetime_elli',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 29, 12, 29, 8, 980024), null=True),
        ),
    ]