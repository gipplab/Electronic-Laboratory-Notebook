# Generated by Django 3.1.3 on 2023-11-21 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Analysis', '0009_auto_20231107_2039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pointsshift',
            name='Type_pos',
            field=models.TextField(blank=True, choices=[('upper_on_hill', 'upper_on_hill'), ('upper_on_plate', 'upper_on_plate'), ('lower_in_groove', 'lower_in_groove'), ('upper_in_groove', 'upper_in_groove'), ('white_lower_in_groove', 'white_lower_in_groove'), ('white_upper_in_groove', 'white_upper_in_groove')], null=True),
        ),
    ]
