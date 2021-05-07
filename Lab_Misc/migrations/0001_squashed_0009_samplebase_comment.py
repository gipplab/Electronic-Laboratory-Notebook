# Generated by Django 3.1.3 on 2021-05-04 20:31

import datetime
from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    replaces = [('Lab_Misc', '0001_initial'), ('Lab_Misc', '0002_auto_20200714_2019'), ('Lab_Misc', '0003_sampleblank_description'), ('Lab_Misc', '0004_project_projectentry'), ('Lab_Misc', '0005_auto_20200817_2050'), ('Lab_Misc', '0006_samplebase_parent'), ('Lab_Misc', '0007_pseudosample'), ('Lab_Misc', '0008_samplebrushpnipaaminfasil'), ('Lab_Misc', '0009_samplebase_comment')]

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Polymer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Material', models.TextField(blank=True, null=True)),
                ('Manufactured', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Manufacturer', models.TextField(blank=True, null=True)),
                ('Number_average_kDa', models.FloatField(blank=True, null=True)),
                ('Weight_average_kDa', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SamplePseudoBrushPDMSGlass',
            fields=[
                ('samplebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Lab_Misc.samplebase')),
                ('Parent', models.TextField(blank=True, null=True)),
                ('Birth', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Death', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Length_cm', models.FloatField(blank=True, null=True)),
                ('Width_cm', models.FloatField(blank=True, null=True)),
                ('Thickness_PDMS_nm', models.FloatField(blank=True, null=True)),
                ('Polymer', models.ManyToManyField(blank=True, to='Lab_Misc.Polymer')),
            ],
            bases=('Lab_Misc.samplebase',),
        ),
        migrations.CreateModel(
            name='SampleBrushPNiPAAmSi',
            fields=[
                ('samplebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Lab_Misc.samplebase')),
                ('Parent', models.TextField(blank=True, null=True)),
                ('Birth', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Death', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Length_cm', models.FloatField(blank=True, null=True)),
                ('Width_cm', models.FloatField(blank=True, null=True)),
                ('Thickness_SiO2_nm', models.FloatField(blank=True, null=True)),
                ('Thickness_PGMA_nm', models.FloatField(blank=True, null=True)),
                ('Thickness_PNiPAAm_nm', models.FloatField(blank=True, null=True)),
                ('Number_on_back', models.IntegerField(blank=True, null=True)),
                ('Polymer', models.ManyToManyField(blank=True, to='Lab_Misc.Polymer')),
            ],
            bases=('Lab_Misc.samplebase',),
        ),
        migrations.CreateModel(
            name='SampleBlank',
            fields=[
                ('samplebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Lab_Misc.samplebase')),
                ('Material', models.TextField(blank=True, null=True)),
                ('Length_cm', models.FloatField(blank=True, null=True)),
                ('Width_cm', models.FloatField(blank=True, null=True)),
                ('Description', models.TextField(blank=True, null=True)),
            ],
            bases=('Lab_Misc.samplebase',),
        ),
        migrations.CreateModel(
            name='ProjectEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, db_column='Name:', null=True, unique=True)),
                ('Description', models.TextField(blank=True, db_column='Description:', null=True)),
                ('Conclusion', models.TextField(blank=True, db_column='Conclusion:', null=True)),
                ('Issued', models.DateTimeField(blank=True, default=datetime.datetime.now)),
                ('DueDate', models.DateTimeField(blank=True, default=datetime.datetime(2023, 12, 31, 0, 0))),
                ('Fineshed', models.BooleanField(verbose_name='Fineshed:')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, db_column='Name:', null=True, unique=True)),
                ('Description', models.TextField(blank=True, db_column='Description:', null=True)),
                ('Issued', models.DateTimeField(blank=True, default=datetime.datetime.now)),
                ('DueDate', models.DateTimeField(blank=True, default=datetime.datetime(2023, 12, 31, 0, 0))),
                ('Fineshed', models.BooleanField(verbose_name='Fineshed:')),
                ('Priory', models.CharField(choices=[('1', 'Critical'), ('2', 'High'), ('3', 'Medium'), ('4', 'Low')], default='3', max_length=1)),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('Entry', models.ManyToManyField(blank=True, to='Lab_Misc.ProjectEntry')),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='Lab_Misc.project')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PseudoSample',
            fields=[
                ('samplebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Lab_Misc.samplebase')),
            ],
            options={
                'abstract': False,
            },
            bases=('Lab_Misc.samplebase',),
        ),
        migrations.CreateModel(
            name='SampleBrushPNiPAAmInfasil',
            fields=[
                ('samplebase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='Lab_Misc.samplebase')),
                ('Parent', models.TextField(blank=True, null=True)),
                ('Birth', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Death', models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0))),
                ('Diameter_cm', models.FloatField(blank=True, null=True)),
                ('Thickness_PGMA_nm', models.FloatField(blank=True, null=True)),
                ('Thickness_PNiPAAm_nm', models.FloatField(blank=True, null=True)),
                ('Number_on_back', models.IntegerField(blank=True, null=True)),
                ('Polymer', models.ManyToManyField(blank=True, to='Lab_Misc.Polymer')),
            ],
            options={
                'abstract': False,
            },
            bases=('Lab_Misc.samplebase',),
        ),
        migrations.CreateModel(
            name='SampleBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('level', models.PositiveIntegerField(default=0, editable=False)),
                ('lft', models.PositiveIntegerField(default=1, editable=False)),
                ('rght', models.PositiveIntegerField(default=2, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, default=1, editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='Lab_Misc.samplebase')),
                ('Comment', models.TextField(blank=True, null=True)),
            ],
        ),
    ]