from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Exp_Main", "0014_yfl_cellpose_default_and_processed_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="yfl",
            name="LIF_Signal_Index",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
