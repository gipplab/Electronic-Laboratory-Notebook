# Generated by Django 3.1.3 on 2021-05-06 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Lab_Misc', '0001_squashed_0009_samplebase_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='samplebase',
            name='level',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='samplebase',
            name='lft',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='samplebase',
            name='rght',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='samplebase',
            name='tree_id',
            field=models.PositiveIntegerField(db_index=True, editable=False),
        ),
    ]
