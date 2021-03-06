# Generated by Django 3.1.3 on 2021-05-04 20:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('Analysis', '0001_initial'), ('Analysis', '0002_auto_20210307_0017'), ('Analysis', '0003_auto_20210307_0032'), ('Analysis', '0004_auto_20210311_1606')]

    initial = True

    dependencies = [
        ('Lab_Dash', '0001_squashed_0062_auto_20210427_1647'),
        ('Exp_Main', '0001_squashed_0053_auto_20210427_1647'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Comparison',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ],
                    options={
                        'db_table': 'Analysis_comparison',
                    },
                ),
            ],
        ),
        migrations.AddField(
            model_name='comparison',
            name='Dash',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.comparison'),
        ),
        migrations.AddField(
            model_name='comparison',
            name='ExpBase',
            field=models.ManyToManyField(blank=True, to='Exp_Main.ExpBase'),
        ),
        migrations.AddField(
            model_name='comparison',
            name='Name',
            field=models.TextField(blank=True, null=True, unique=True),
        ),
        migrations.AlterModelTable(
            name='comparison',
            table=None,
        ),
        migrations.CreateModel(
            name='OszBaseParam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Drop_Nr', models.IntegerField(blank=True, null=True)),
                ('LoR_CL', models.TextField(blank=True, choices=[('Left', 'Left'), ('Right', 'Right')], null=True)),
                ('Max_CL', models.FloatField(blank=True, null=True)),
                ('Max_CA', models.FloatField(blank=True, null=True)),
                ('Min_CA', models.FloatField(blank=True, null=True)),
                ('Min_AdvCA', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OszFitRes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Drop_Nr', models.IntegerField(blank=True, null=True)),
                ('LoR_CL', models.TextField(blank=True, choices=[('Left', 'Left'), ('Right', 'Right')], null=True)),
                ('ErroVal', models.TextField(blank=True, choices=[('Value', 'Value'), ('Error', 'Error')], null=True)),
                ('x_pos', models.FloatField(blank=True, null=True)),
                ('y_pos', models.FloatField(blank=True, null=True)),
                ('Step_width', models.FloatField(blank=True, null=True)),
                ('Step_hight', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OszAnalysisJoin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True, unique=True)),
                ('Dash', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.oszanalysis')),
                ('OszAnalysis', models.ManyToManyField(blank=True, to='Analysis.OszAnalysis')),
            ],
        ),
        migrations.CreateModel(
            name='OszDerivedRes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Drop_Nr', models.IntegerField(blank=True, null=True)),
                ('LoR_CL', models.TextField(blank=True, choices=[('Left', 'Left'), ('Right', 'Right')], null=True)),
                ('Hit_prec', models.FloatField(blank=True, null=True)),
                ('Fit_score', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OszAnalysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Drop_center', models.FloatField(blank=True, null=True)),
                ('Exp', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Exp_Main.expbase')),
                ('OszBaseParam', models.ManyToManyField(blank=True, to='Analysis.OszBaseParam')),
                ('OszFitRes', models.ManyToManyField(blank=True, to='Analysis.OszFitRes')),
                ('Hit_prec', models.FloatField(blank=True, null=True)),
                ('OszDerivedRes', models.ManyToManyField(blank=True, to='Analysis.OszDerivedRes')),
            ],
        ),
    ]
