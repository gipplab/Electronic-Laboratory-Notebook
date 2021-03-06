# Generated by Django 3.1.3 on 2021-05-16 13:27

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0005_auto_20210516_1527'),
        ('Lab_Dash', '0005_auto_20210516_1527'),
        ('Exp_Main', '0004_auto_20210506_2243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 15, 27, 22, 850169), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2021, 5, 16, 15, 27, 22, 850169), null=True),
        ),
        migrations.CreateModel(
            name='RSD',
            fields=[
                ('expbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Exp_Main.expbase')),
                ('Link', models.TextField(blank=True, null=True)),
                ('Link_Data', models.TextField(blank=True, null=True)),
                ('Link_PDF', models.TextField(blank=True, null=True)),
                ('Link_Osz_join_LSP', models.TextField(blank=True, null=True)),
                ('Temp_Observation', models.TextField(blank=True, null=True)),
                ('Temp_Hypothesis', models.TextField(blank=True, null=True)),
                ('Temp_Mixing_ratio', models.TextField(blank=True, null=True)),
                ('Temp_Atmosphere_relax', models.TextField(blank=True, null=True)),
                ('Temp_Flowrate', models.TextField(blank=True, null=True)),
                ('Temp_Volume', models.TextField(blank=True, null=True)),
                ('Temp_Buzz_word', models.TextField(blank=True, null=True)),
                ('Temp_Bath_time', models.TextField(blank=True, null=True)),
                ('Dash', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.oca')),
                ('Liquid', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Exp_Main.liquid')),
                ('Sub_Exp', models.ManyToManyField(blank=True, to='Exp_Sub.ExpBase')),
            ],
            bases=('Exp_Main.expbase',),
        ),
    ]
