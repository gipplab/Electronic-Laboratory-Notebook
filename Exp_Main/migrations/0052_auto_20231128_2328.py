# Generated by Django 3.1.3 on 2023-11-29 04:28

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0051_auto_20231121_1522'),
    ]

    operations = [
        migrations.AddField(
            model_name='grv',
            name='Link_Data_processed',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 28, 23, 28, 36, 494398), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 11, 28, 23, 28, 36, 495402), null=True),
        ),
    ]
