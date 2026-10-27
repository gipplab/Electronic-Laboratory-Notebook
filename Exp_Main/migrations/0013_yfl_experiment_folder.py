from django.db import migrations


YFL_VIDEO_PATH = (
    '01_Experimental/02_Experiments/01_Main_Exp/03_Leica_Microscope/'
    '01_Yeast_FLIM/01_Videos'
)


def update_yfl_path(apps, schema_editor):
    ExpPath = apps.get_model('Exp_Main', 'ExpPath')
    ExpPath.objects.filter(Abbrev='YFL').update(Path=YFL_VIDEO_PATH)


class Migration(migrations.Migration):

    dependencies = [
        ('Exp_Main', '0012_yfl_yeast_flim'),
    ]

    operations = [
        migrations.RunPython(update_yfl_path, migrations.RunPython.noop),
    ]
