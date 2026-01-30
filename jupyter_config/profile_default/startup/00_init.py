# jupyter_config/profile_default/startup/00_init.py

import os
import django
import sys

print("--- Initialisiere Laborbuch-Umgebung... ---")

# 1. Pfad zum Projekt hinzufügen (damit er 'Exp_Main' etc. findet)
# Wir gehen davon aus, dass Jupyter im Hauptordner gestartet wird
sys.path.append(os.getcwd())

# 2. Django Settings setzen
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# 3. Django starten
django.setup()

# 4. Deine Modelle importieren
from django.db.models import Model
from Exp_Main.models import ExpBase
from Exp_Sub.models import ExpBase as ExpBase_sub
from Lab_Misc import General
from Lab_Misc import Load_Data

print("--- Fertig! ExpBase, Load_Data usw. sind geladen. ---")