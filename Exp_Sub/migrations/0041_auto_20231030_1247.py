# Generated by Django 3.1.3 on 2023-10-30 16:47

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0040_auto_20231030_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='hbk',
            name='Link_Data',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='gas',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 47, 56, 69365), null=True),
        ),
        migrations.AlterField(
            model_name='gas',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 47, 56, 69886), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 47, 56, 68854), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 12, 47, 56, 68854), null=True),
        ),
    ]
