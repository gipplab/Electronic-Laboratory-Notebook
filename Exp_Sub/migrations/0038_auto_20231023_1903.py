# Generated by Django 3.1.3 on 2023-10-23 23:03

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0037_auto_20231017_1504'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gas',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 23, 19, 3, 23, 394728), null=True),
        ),
        migrations.AlterField(
            model_name='gas',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 23, 19, 3, 23, 394728), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 23, 19, 3, 23, 393735), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 23, 19, 3, 23, 393735), null=True),
        ),
    ]