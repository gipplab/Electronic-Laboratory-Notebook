import django.db.models.deletion
from django.db import migrations, models


def add_yeast_flim_device(apps, schema_editor):
    ExpPath = apps.get_model('Exp_Main', 'ExpPath')
    FileEnding = apps.get_model('Exp_Main', 'FileEnding')
    ending, _ = FileEnding.objects.get_or_create(
        Ending='lif', defaults={'Name': 'Leica LIF'}
    )
    device = ExpPath.objects.filter(Abbrev='YFL').first()
    if device is None:
        last_tree_id = ExpPath.objects.order_by('-tree_id').values_list('tree_id', flat=True).first() or 0
        device = ExpPath.objects.create(
            Abbrev='YFL',
            Name='Yeast FLIM',
            Path='Documents/Hefen',
            lft=1,
            rght=2,
            tree_id=last_tree_id + 1,
            level=0,
        )
    else:
        device.Name = 'Yeast FLIM'
        device.save()
    device.File_ending.add(ending)


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0011_alter_liquid_born_alter_liquid_death'),
    ]

    operations = [
        migrations.CreateModel(
            name='YFL',
            fields=[
                ('expbase_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='Exp_Main.expbase',
                )),
                ('Link', models.TextField(blank=True, null=True)),
                ('Segmentation_Image', models.TextField(blank=True, null=True)),
                ('Signal_Image', models.TextField(blank=True, null=True)),
                ('Cellpose_Model', models.CharField(default='cpsam', max_length=255)),
                ('Cellpose_Diameter', models.FloatField(blank=True, null=True)),
                ('Segmentation_Channel', models.PositiveIntegerField(default=0)),
                ('Segmentation_Time', models.PositiveIntegerField(default=0)),
                ('Segmentation_Z', models.PositiveIntegerField(default=0)),
                ('Signal_Channel', models.PositiveIntegerField(default=0)),
                ('Signal_Z', models.PositiveIntegerField(default=0)),
                ('Min_Cell_Area', models.PositiveIntegerField(default=1)),
                ('Max_Cell_Area', models.PositiveIntegerField(blank=True, null=True)),
                ('Background_Ring', models.PositiveIntegerField(default=3)),
                ('Analysis_Status', models.CharField(
                    choices=[
                        ('not_started', 'Not started'),
                        ('queued', 'Queued'),
                        ('running', 'Running'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                    ],
                    default='not_started',
                    max_length=20,
                )),
                ('Analysis_Result', models.TextField(blank=True, null=True)),
                ('Analysis_Error', models.TextField(blank=True, null=True)),
            ],
            bases=('Exp_Main.expbase',),
        ),
        migrations.RunPython(add_yeast_flim_device, migrations.RunPython.noop),
    ]
