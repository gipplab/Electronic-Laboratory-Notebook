# Generated by Django 3.1.3 on 2021-05-16 17:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0009_auto_20210516_1912'),
        ('Lab_Misc', '0005_auto_20210516_1759'),
    ]

    operations = [
        migrations.AddField(
            model_name='gassesscript',
            name='Name_of_gas',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='Exp_Sub.gas'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='gassesscript',
            name='Name',
            field=models.TextField(blank=True, db_column='Name:', null=True),
        ),
        migrations.AlterField(
            model_name='oszscriptgen',
            name='Name',
            field=models.TextField(blank=True, db_column='Name:', null=True),
        ),
    ]
