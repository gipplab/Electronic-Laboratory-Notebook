# Generated by Django 3.1.3 on 2022-03-18 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Misc', '0007_auto_20210517_1446'),
    ]

    operations = [
        migrations.AddField(
            model_name='oszscriptgen',
            name='max_time',
            field=models.FloatField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name='oszscriptgen',
            name='max_time_pls_increase',
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]