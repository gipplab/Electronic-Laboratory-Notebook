# Generated by Django 3.1.3 on 2022-08-22 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Misc', '0009_samplehydrogelpnipaam'),
    ]

    operations = [
        migrations.AddField(
            model_name='oszscriptgen',
            name='Temperatures',
            field=models.TextField(blank=True, null=True),
        ),
    ]
