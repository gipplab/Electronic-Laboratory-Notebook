# Generated by Django 3.1.3 on 2021-05-17 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Misc', '0006_auto_20210516_1912'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gassesscript',
            name='Periodicity',
            field=models.IntegerField(blank=True, default=3, null=True),
        ),
        migrations.AlterField(
            model_name='oszscriptgen',
            name='number_of_cycles',
            field=models.IntegerField(blank=True, default=9, null=True),
        ),
    ]