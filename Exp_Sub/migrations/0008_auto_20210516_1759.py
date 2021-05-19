# Generated by Django 3.1.3 on 2021-05-16 15:59

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0007_auto_20210516_1746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gas',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 17, 57, 58, 209860), null=True),
        ),
        migrations.AlterField(
            model_name='gas',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 17, 57, 58, 209860), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 17, 57, 58, 208850), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 17, 57, 58, 208850), null=True),
        ),
    ]
