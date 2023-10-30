# Generated by Django 3.1.3 on 2023-10-30 15:42

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Sub', '0038_auto_20231023_1903'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gas',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 11, 42, 14, 158833), null=True),
        ),
        migrations.AlterField(
            model_name='gas',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 11, 42, 14, 159333), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Born',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 11, 42, 14, 158334), null=True),
        ),
        migrations.AlterField(
            model_name='liquid',
            name='Death',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 30, 11, 42, 14, 158334), null=True),
        ),
        migrations.CreateModel(
            name='HBK',
            fields=[
                ('expbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Exp_Sub.expbase')),
                ('Link', models.TextField(blank=True, null=True)),
                ('Liquid', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Exp_Sub.liquid')),
            ],
            bases=('Exp_Sub.expbase',),
        ),
    ]