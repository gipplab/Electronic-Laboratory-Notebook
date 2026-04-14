from django.shortcuts import render
import os
import threading
from Analysis.Osz_Drop import Osz_Drop_Analysis
from Analysis.Osz_Drop_RSD import Osz_Drop_Analysis as Osz_Drop_Analysis_RSD
from Analysis.models import OszAnalysis, OszBaseParam, OszFitRes, OszAnalysisJoin, OszDerivedRes
from Analysis.models import DafAnalysis, GrvAnalysisJoin
from .tables import Comparison_table, OszAnalysis_table, get_Table, RSD_CA_Mess_table
from .tables import DafAnalysis_table, GrvAnalysis_table
from Exp_Main.models import RSD, DAF, ExpBase
import socket
import subprocess
import time
import sys
from django.shortcuts import render, redirect
from django.conf import settings

from .models import MFPAnalysis
from .scripts.MFP_Analyze import run_analysis
from Lab_Dash.models import MFP # Dein Experiment Model
from .scripts.MFP_Analyze import run_full_analysis

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import atexit
import subprocess
import signal
import atexit
from django.conf import settings
from django.shortcuts import render, redirect
# Falls du dein Hybrid-Skript schon gespeichert hast, hier importieren:
# from .scripts.MFP_Cellpose_Hybrid import run_hybrid_cellpose_test

# =========================================================
# 1. VIEW FÜR DEN DASH AI-SCOUT TUNER
# =========================================================
def MFP_Scout_View(request, pk):
    entry = MFP.objects.get(id=pk)
    
    # Sicherstellen, dass ein Analyse-Objekt existiert
    analysis, created = MFPAnalysis.objects.get_or_create(Entry=entry)
    
    # ID in Session speichern für Dash
    request.session['django_plotly_dash'] = {'MFP_id': pk}
    dash_context = {'entry-id': {'data': pk}}

    # Wir rendern ein neues Template speziell für den Scout
    return render(request, 'Analysis_Scout.html', {'entry': entry, 'analysis': analysis, 'dash_context': dash_context})


# =========================================================
# VIEW FÜR DAS MFP DASHBOARD
# =========================================================
def MFP_Dashboard_View(request, pk):
    entry = MFP.objects.get(id=pk)
    analysis, created = MFPAnalysis.objects.get_or_create(Entry=entry)
    
    # ID in Session speichern für Dash, damit die Dash App weiß, welches Video sie laden muss
    request.session['django_plotly_dash'] = {'MFP_id': pk}
    dash_context = {'entry-id': {'data': pk}}

    return render(request, 'Analysis_Dashboard.html', {'entry': entry, 'analysis': analysis, 'dash_context': dash_context})

# =========================================================
# 2. API ENDPOINT FÜR DEN KI-BUTTON (Cellpose Background-Task)
# =========================================================
@csrf_exempt 
def api_run_cellpose(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry_id = data.get('entry_id')
            frame = int(data.get('frame', 0))
            diameter = int(data.get('diameter', 99))
            minmass = int(data.get('minmass', 100))
            
            model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/models/Polymersome_20260411_121237'

            # Hier rufst du später deine Cellpose-Funktion auf:
            # result = run_hybrid_cellpose_test(entry_id, frame, diameter, minmass, model_path)
            
            # DUMMY-ANTWORT (Zum Testen, ob der Button im Frontend klappt)
            result = {
                "status": "success", 
                "found_points": 12,
                "valid_cells": 10,
                "data": [
                    {"radius": 50, "circ": 0.95},
                    {"radius": 52, "circ": 0.91}
                ]
            }
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
            
    return JsonResponse({"error": "Only POST allowed"}, status=400)

def MFP_Analysis_View(request, pk):
    entry = MFP.objects.get(id=pk)
    
    # Sicherstellen, dass ein Analyse-Objekt existiert (Datenkarte)
    analysis, created = MFPAnalysis.objects.get_or_create(Entry=entry)
    
    if request.method == 'POST':
        if 'save_params' in request.POST:
            # Parameter speichern
            analysis.Particle_Radius = int(request.POST.get('radius'))
            analysis.Threshold = float(request.POST.get('threshold'))
            analysis.save()
            
        elif 'run_analysis' in request.POST:
            # Analyse starten
            success = run_analysis(analysis)
            if success:
                # Seite neu laden um Dash anzuzeigen
                return redirect('MFP_Analysis_View', pk=pk)

    # ID in Session speichern für Dash
    request.session['django_plotly_dash'] = {'MFP_id': pk}

    return render(request, 'Analysis_MFP.html', {'entry': entry, 'analysis': analysis})

# Hilfsfunktion: Checkt, ob Port 8888 schon belegt ist (Jupyter läuft)
def is_jupyter_running():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Timeout kurz setzen, damit die Seite nicht hängt
    sock.settimeout(1) 
    result = sock.connect_ex(('127.0.0.1', 8888))
    sock.close()
    return result == 0

def cleanup_jupyter_on_exit():
    """Wird automatisch vom System aufgerufen, wenn der Django-Server stoppt."""
    print("Django fährt herunter. Beende verwaiste Jupyter-Prozesse...")
    try:
        # Sucht und beendet alle Hintergrundprozesse, die 'jupyter' im Namen haben
        subprocess.run(['pkill', '-f', 'jupyter'], check=False)
    except Exception as e:
        print(f"Fehler beim Beenden von Jupyter: {e}")

def is_qcluster_running():
    """Prüft, ob der Q-Cluster Prozess bereits aktiv ist."""
    try:
        # Sucht nach dem Prozessnamen in der Prozessliste
        output = subprocess.check_output(['pgrep', '-f', 'manage.py qcluster'])
        return True
    except subprocess.CalledProcessError:
        return False

def cleanup_processes_on_exit():
    """Beendet Jupyter UND den Q-Cluster beim Herunterfahren von Django."""
    print("🛑 Django-Server beendet. Räume Hintergrundprozesse auf...")
    try:
        # Beendet alle Prozesse, die 'jupyter' oder 'qcluster' im Aufruf haben
        subprocess.run(['pkill', '-f', 'jupyter'], check=False)
        subprocess.run(['pkill', '-f', 'manage.py qcluster'], check=False)
    except Exception as e:
        print(f"Fehler beim Aufräumen: {e}")

# Registriert die Aufräum-Funktion beim Start von Django
if 'runserver' in sys.argv:
    atexit.register(cleanup_processes_on_exit)

# --- Die angepasste Index-View ---

def index(request):
    cluster_status = is_qcluster_running()
    jupyter_status = is_jupyter_running()

    if request.method == 'POST':
        # FALL A: KI-Manager (Q-Cluster) starten
        if 'start_cluster' in request.POST:
            if not cluster_status:
                print("🚀 Starte Django-Q2 Manager...")
                # Startet den Prozess im Hintergrund
                subprocess.Popen(
                    [sys.executable, 'manage.py', 'qcluster'],
                    cwd=settings.BASE_DIR
                )
            return redirect('Analysis:index')

        # FALL B: Jupyter Lab starten (dein bestehender Code)
        elif 'run_script' in request.POST:
            if not jupyter_status:
                script_path = os.path.join(settings.BASE_DIR, 'start_analysis.sh')
                subprocess.Popen(['/bin/bash', script_path], cwd=settings.BASE_DIR)
            
            host = request.get_host().split(':')[0] 
            return redirect(f"http://{host}:8888/lab")

    context = {
        'cluster_running': cluster_status,
        'jupyter_running': jupyter_status,
    }
    return render(request, 'Analysis.html', context)

def OszAnalysis_view(request):
    model = OszAnalysisJoin.objects.all()
    table = OszAnalysis_table(model)
    context = {'table': table}
    return render(request, 'Comparison.html', context)

def RSDAnalysis_view(request):
    model = RSD.objects.all()
    table = RSD_CA_Mess_table(model)
    context = {'table': table}
    return render(request, 'Comparison.html', context)

def DafAnalysis_view(request):
    model = DafAnalysis.objects.all()
    table = DafAnalysis_table(model)
    context = {'table': table}
    return render(request, 'Comparison.html', context)

def GrvAnalysis_view(request):
    model = GrvAnalysisJoin.objects.all()
    table = GrvAnalysis_table(model)
    context = {'table': table}
    return render(request, 'Comparison.html', context)

def OszAnalysis_table_view(request, pk):
    model = OszAnalysis.objects.all()
    table = OszAnalysis_table(model)
    context = {'stuff': table}
    table_class = get_Table('OszBaseParam')
    context['table_parameters'] = table_class(OszAnalysis.objects.get(id = pk).OszBaseParam.all())
    table_class = get_Table('OszFitRes')
    context['table_fit'] = table_class(OszAnalysis.objects.get(id = pk).OszFitRes.all())
    table_class = get_Table('OszDerivedRes')
    context['table_derived'] = table_class(OszAnalysis.objects.get(id = pk).OszDerivedRes.all())
    context['Drop_center'] = OszAnalysis.objects.get(id = pk).Drop_center
    context['Experiment_Name'] = OszAnalysis.objects.get(id = pk).Exp.Name
    context['Hit_prec'] = OszAnalysis.objects.get(id = pk).Hit_prec
    if request.method == 'POST' and 'Analyse_osz' in request.POST:
        Exp_Base_id = OszAnalysis.objects.get(id = pk).Exp.id
        str_dev = str(ExpBase.objects.get(pk = Exp_Base_id).Device.Abbrev)
        if str_dev == 'OCA':
            Osz_Drop_Analysis(OszAnalysis.objects.get(id = pk).Exp.id)
        elif str_dev == 'RSD':
            Osz_Drop_Analysis_RSD(OszAnalysis.objects.get(id = pk).Exp.id)
    return render(request, 'OszAnalysis_table.html', context)

def DafAnalysis_table_view(request, pk):
    model = DafAnalysis.objects.all()
    table = DafAnalysis_table(model)
    context = {'stuff': table}
    if request.method == 'POST' and 'Analyse_daf' in request.POST:
        # Daf_Analysis(DafAnalysis.objects.get(id = pk).Exp.id)
        pass
    return render(request, 'DafAnalysis_table.html', context)

def cluster_live_log(request, entry_id):
    """Liest die temporäre Log-Datei des Q-Clusters für ein bestimmtes Experiment aus."""
    # WICHTIG: Pfad an Cellpose_Cement.py angepasst
    log_path = f"/tmp/cellpose_log_{entry_id}.txt"
    
    # Wenn die Datei noch nicht existiert (Worker startet gerade erst)
    if not os.path.exists(log_path):
        return JsonResponse({
            "status": "waiting", 
            "log": f"⏳ Warte auf Cluster...\nDer Worker bereitet die Umgebung für Entry {entry_id} vor. Log-Datei wird gleich erstellt."
        })

    try:
        # Die letzten 30 Zeilen auslesen, damit das Frontend nicht überlastet wird
        with open(log_path, 'r') as f:
            lines = f.readlines()[-30:]
            return JsonResponse({"status": "running", "log": "".join(lines)})
    except Exception as e:
        return JsonResponse({"status": "error", "log": f"❌ Fehler beim Lesen des Logs: {str(e)}"})