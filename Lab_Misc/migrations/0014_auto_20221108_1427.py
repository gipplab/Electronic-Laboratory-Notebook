# Generated by Django 3.1.3 on 2022-11-08 13:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Misc', '0013_samplegelpdms'),
    ]

    operations = [
        migrations.RenameField(
            model_name='samplegelpdms',
            old_name='Thickness_PNiPAAm_nm',
            new_name='Thickness_PNiPAAm_mm',
        ),
    ]