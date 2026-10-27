from django.db import migrations, models


YFL_PROCESSED_PATH = (
    "01_Experimental/02_Experiments/01_Main_Exp/03_Leica_Microscope/"
    "01_Yeast_FLIM/03_Processed_Data"
)


def set_yfl_processed_path(apps, schema_editor):
    ExpPath = apps.get_model("Exp_Main", "ExpPath")
    ExpPath.objects.filter(Abbrev="YFL").update(PathProcessedData=YFL_PROCESSED_PATH)


class Migration(migrations.Migration):

    dependencies = [
        ("Exp_Main", "0013_yfl_experiment_folder"),
    ]

    operations = [
        migrations.AlterField(
            model_name="yfl",
            name="Cellpose_Model",
            field=models.CharField(default="cpsam_v2", max_length=255),
        ),
        migrations.RunPython(set_yfl_processed_path, migrations.RunPython.noop),
    ]
