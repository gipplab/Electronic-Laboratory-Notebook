# Generated by Django 3.1.3 on 2021-05-04 20:32

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('Lab_Dash', '0001_initial'), ('Lab_Dash', '0002_oca_name'), ('Lab_Dash', '0003_kur'), ('Lab_Dash', '0004_auto_20200722_1620'), ('Lab_Dash', '0005_oca_time_diff_pump'), ('Lab_Dash', '0006_sel'), ('Lab_Dash', '0007_sel_start_datetime_elli'), ('Lab_Dash', '0008_auto_20200831_1434'), ('Lab_Dash', '0009_auto_20200901_2129'), ('Lab_Dash', '0010_auto_20200901_2139'), ('Lab_Dash', '0011_auto_20200901_2147'), ('Lab_Dash', '0012_auto_20200901_2324'), ('Lab_Dash', '0013_auto_20200903_1207'), ('Lab_Dash', '0014_auto_20200903_1210'), ('Lab_Dash', '0015_auto_20200918_1347'), ('Lab_Dash', '0016_auto_20200919_1838'), ('Lab_Dash', '0017_auto_20200921_1830'), ('Lab_Dash', '0018_auto_20200921_1845'), ('Lab_Dash', '0019_auto_20200921_1847'), ('Lab_Dash', '0020_auto_20200921_1848'), ('Lab_Dash', '0021_auto_20200921_1947'), ('Lab_Dash', '0022_auto_20201026_0906'), ('Lab_Dash', '0023_auto_20201026_0914'), ('Lab_Dash', '0024_auto_20201104_1900'), ('Lab_Dash', '0025_auto_20201105_1707'), ('Lab_Dash', '0026_auto_20201106_1546'), ('Lab_Dash', '0027_auto_20201106_1554'), ('Lab_Dash', '0028_auto_20201106_1618'), ('Lab_Dash', '0029_auto_20201108_1947'), ('Lab_Dash', '0030_auto_20201111_1043'), ('Lab_Dash', '0031_auto_20201111_1102'), ('Lab_Dash', '0032_auto_20201111_1113'), ('Lab_Dash', '0033_auto_20201111_1119'), ('Lab_Dash', '0034_auto_20201111_1238'), ('Lab_Dash', '0035_auto_20201111_2048'), ('Lab_Dash', '0036_auto_20201111_2054'), ('Lab_Dash', '0037_auto_20201112_1210'), ('Lab_Dash', '0038_auto_20201117_0950'), ('Lab_Dash', '0039_auto_20201120_1832'), ('Lab_Dash', '0040_auto_20201122_2222'), ('Lab_Dash', '0041_auto_20201123_1908'), ('Lab_Dash', '0042_auto_20201129_1157'), ('Lab_Dash', '0043_auto_20201129_1332'), ('Lab_Dash', '0044_auto_20201201_1302'), ('Lab_Dash', '0045_auto_20201201_2115'), ('Lab_Dash', '0046_auto_20201207_1436'), ('Lab_Dash', '0047_auto_20210211_1719'), ('Lab_Dash', '0048_auto_20210211_1947'), ('Lab_Dash', '0049_auto_20210302_2059'), ('Lab_Dash', '0050_auto_20210306_2227'), ('Lab_Dash', '0051_auto_20210307_0017'), ('Lab_Dash', '0052_auto_20210307_0026'), ('Lab_Dash', '0053_auto_20210307_0032'), ('Lab_Dash', '0054_auto_20210307_1534'), ('Lab_Dash', '0055_auto_20210307_1633'), ('Lab_Dash', '0056_auto_20210308_1224'), ('Lab_Dash', '0057_auto_20210310_1727'), ('Lab_Dash', '0058_auto_20210310_1742'), ('Lab_Dash', '0059_auto_20210310_1908'), ('Lab_Dash', '0060_auto_20210311_1606'), ('Lab_Dash', '0061_auto_20210322_1601'), ('Lab_Dash', '0062_auto_20210427_1647')]

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='KUR',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('CA_high_degree', models.FloatField(blank=True, null=True)),
                ('CA_low_degree', models.FloatField(blank=True, null=True)),
                ('BD_high_mm', models.FloatField(blank=True, null=True)),
                ('BD_low_mm', models.FloatField(blank=True, null=True)),
                ('Time_high_sec', models.FloatField(blank=True, null=True)),
                ('Time_low_sec', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OCA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('CA_high_degree', models.FloatField(blank=True, null=True)),
                ('CA_low_degree', models.FloatField(blank=True, null=True)),
                ('BD_high_mm', models.FloatField(blank=True, null=True)),
                ('BD_low_mm', models.FloatField(blank=True, null=True)),
                ('Time_high_sec', models.FloatField(blank=True, null=True)),
                ('Time_low_sec', models.FloatField(blank=True, null=True)),
                ('Name', models.TextField(blank=True, null=True, unique=True)),
                ('Cycle_drop_1_sec', models.FloatField(blank=True, null=True)),
                ('Cycle_drop_2_sec', models.FloatField(blank=True, null=True)),
                ('Cycle_drop_3_sec', models.FloatField(blank=True, null=True)),
                ('Cycle_drop_4_sec', models.FloatField(blank=True, null=True)),
                ('Cycle_drop_5_sec', models.FloatField(blank=True, null=True)),
                ('Cycle_drop_6_sec', models.FloatField(blank=True, null=True)),
                ('Time_diff_pump', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SFG',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='SFG_kin_drive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Time_high_sec', models.FloatField(blank=True, null=True)),
                ('Time_low_sec', models.FloatField(blank=True, null=True)),
                ('Signal_high', models.FloatField(blank=True, null=True)),
                ('Signal_low', models.FloatField(blank=True, null=True)),
                ('Wavenumber_high', models.FloatField(blank=True, null=True)),
                ('Wavenumber_low', models.FloatField(blank=True, null=True)),
                ('Group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.grp')),
            ],
        ),
        migrations.CreateModel(
            name='SFG_kin_3D',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Signal_high', models.FloatField(blank=True, null=True)),
                ('Group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.grp')),
                ('Signal_low', models.FloatField(blank=True, null=True)),
                ('Time_high_sec', models.FloatField(blank=True, null=True)),
                ('Time_low_sec', models.FloatField(blank=True, null=True)),
                ('Wavenumber_high', models.FloatField(blank=True, null=True)),
                ('Wavenumber_low', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SFG_abrastern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Graph_distance', models.FloatField(blank=True, null=True)),
                ('Signal_high', models.FloatField(blank=True, null=True)),
                ('Signal_low', models.FloatField(blank=True, null=True)),
                ('Wavenumber_high', models.FloatField(blank=True, null=True)),
                ('Wavenumber_low', models.FloatField(blank=True, null=True)),
                ('Group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.grp')),
            ],
        ),
        migrations.CreateModel(
            name='GRP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Typ', models.TextField(blank=True, choices=[('SFG_kin_3D', 'Sum frequency generation kinetic'), ('SFG_kin_drive', 'Sum frequency generation kinetic while changing the Position'), ('SFG_abrastern', 'Sum frequency generation at different locations'), ('SFG_cycle', 'Sum frequency generation cycle drops')], null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SFG_cycle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(unique=True)),
                ('Graph_distance', models.FloatField(blank=True, null=True)),
                ('Signal_high', models.FloatField(blank=True, null=True)),
                ('Signal_low', models.FloatField(blank=True, null=True)),
                ('Wavenumber_high', models.FloatField(blank=True, null=True)),
                ('Wavenumber_low', models.FloatField(blank=True, null=True)),
                ('Group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='Lab_Dash.grp')),
            ],
        ),
        migrations.CreateModel(
            name='ComparisonEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True)),
                ('ExpBaseID', models.IntegerField(blank=True, null=True)),
                ('X_high', models.FloatField(blank=True, null=True)),
                ('X_low', models.FloatField(blank=True, null=True)),
                ('Y_high', models.FloatField(blank=True, null=True)),
                ('Y_low', models.FloatField(blank=True, null=True)),
                ('X_shift', models.FloatField(blank=True, null=True)),
                ('Y_shift', models.FloatField(blank=True, null=True)),
                ('Label', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Comparison',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True)),
                ('X_high', models.FloatField(blank=True, null=True)),
                ('X_low', models.FloatField(blank=True, null=True)),
                ('Y_high', models.FloatField(blank=True, null=True)),
                ('Y_low', models.FloatField(blank=True, null=True)),
                ('Entry', models.ManyToManyField(blank=True, to='Lab_Dash.ComparisonEntry')),
                ('Title', models.TextField(blank=True, null=True)),
                ('X_shift', models.FloatField(blank=True, null=True)),
                ('Y_shift', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OszAnalysisEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True)),
                ('Label', models.TextField(blank=True, null=True)),
                ('OszAnalysisID', models.IntegerField(blank=True, null=True)),
                ('X_high', models.FloatField(blank=True, null=True)),
                ('X_low', models.FloatField(blank=True, null=True)),
                ('Y_high', models.FloatField(blank=True, null=True)),
                ('Y_low', models.FloatField(blank=True, null=True)),
                ('X_shift', models.FloatField(blank=True, null=True)),
                ('Y_shift', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='OszAnalysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True)),
                ('Title', models.TextField(blank=True, null=True)),
                ('X_shift', models.FloatField(blank=True, null=True)),
                ('Y_shift', models.FloatField(blank=True, null=True)),
                ('X_high', models.FloatField(blank=True, null=True)),
                ('X_low', models.FloatField(blank=True, null=True)),
                ('Y_high', models.FloatField(blank=True, null=True)),
                ('Y_low', models.FloatField(blank=True, null=True)),
                ('Entry', models.ManyToManyField(blank=True, to='Lab_Dash.OszAnalysisEntry')),
            ],
        ),
        migrations.CreateModel(
            name='SEL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.TextField(blank=True, null=True, unique=True)),
                ('Start_datetime_elli', models.DateTimeField(blank=True, default=datetime.datetime(2021, 4, 27, 16, 47, 33, 239608), null=True)),
            ],
        ),
    ]