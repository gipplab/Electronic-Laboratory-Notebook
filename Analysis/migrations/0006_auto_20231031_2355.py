# Generated by Django 3.1.3 on 2023-11-01 03:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Analysis', '0005_grvanalysis_pointsshift_steadyshift'),
    ]

    operations = [
        migrations.AlterField(
            model_name='steadyshift',
            name='NrAvrgFrame',
            field=models.IntegerField(blank=True, default=3, null=True),
        ),
    ]
