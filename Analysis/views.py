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
import json # Sicherstellen, dass json importiert ist
from .models import MFPAnalysis
from .scripts.MFP_Analyze import run_analysis
import Lab_Dash.dash_apps.MFP_Daily_Dashboard
import Lab_Dash.dash_apps.YFL_Dashboard
from Lab_Dash.models import MFP # Dein Experiment Model
from .scripts.MFP_Analyze import run_full_analysis
from django.shortcuts import get_object_or_404
from Exp_Main.models import MFP as Main_MFP
from Exp_Main.models import YFL
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

    context = {
        'entry': entry, 
        'analysis': analysis, 
        'dash_context': dash_context,
        'page_title': f"Scout {pk}"
    }
    # Wir rendern ein neues Template speziell für den Scout
    return render(request, 'Analysis_Scout.html', context)


# =========================================================
# VIEW FÜR DAS MFP DASHBOARD
# =========================================================
# 🚨 HIER: Wir nehmen 'pk' entgegen, weil urls.py das so schickt!
def MFP_Dashboard_View(request, pk):
    # Wir suchen das Main-Experiment anhand der übergebenen ID (pk)
    entry = get_object_or_404(Main_MFP, id=pk)
    analysis, created = MFPAnalysis.objects.get_or_create(Entry=entry)
    
    # ID in Session speichern für Dash, damit die Dash App weiß, welches Video sie laden muss
    request.session['django_plotly_dash'] = {'MFP_id': pk}
    
    # Dash Context füttern
    dash_context = {'entry-id': {'data': pk}}

    context = {
        'entry': entry, 
        'analysis': analysis, 
        'dash_context': dash_context,
        'page_title': f"Dash {pk}"
    }
    return render(request, 'Analysis_Dashboard.html', context)

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


def YFL_Analysis_View(request, pk):
    """Select a Leica FLIM series and queue the yeast-cell analysis."""
    import math
    from pathlib import Path
    from django.conf import settings

    entry = get_object_or_404(YFL, pk=pk)
    message = ""
    from Analysis.scripts.Yeast_FLIM_Results import yeast_data_root
    data_root = yeast_data_root()
    lif_candidates = []
    lif_error = ""
    lif_path = None
    if entry.Link:
        try:
            from Analysis.scripts.Yeast_FLIM_LIF import resolve_lif_path

            lif_path = resolve_lif_path(entry.Link, data_root, entry.Device.Path)
        except Exception as exc:
            lif_error = f"Could not resolve this Leica LIF file: {exc}"
    if lif_path is not None and lif_path.suffix.lower() != '.lif':
        lif_error = "The linked acquisition is not a Leica .lif file."
    elif lif_path is not None and not lif_path.is_file():
        lif_error = f"The linked Leica LIF file does not exist: {lif_path}"
    elif lif_path is not None:
        try:
            from Analysis.scripts.Yeast_FLIM_LIF import list_lif_candidates
            lif_candidates = list_lif_candidates(lif_path)
            if not lif_candidates:
                lif_error = (
                    "No usable 32-bit FLIM Compressed/Intensity time series with "
                    "a compatible reference image was found in this LIF file."
                )
        except Exception as exc:
            lif_error = f"Could not read this Leica LIF file: {exc}"

    if request.method == 'POST':
        try:
            from Analysis.scripts.Yeast_FLIM_Results import live_status
            current = live_status(entry)  # also converts a dead worker run to 'failed'
            if current['state'] in {'queued', 'running'} and not current['restart_allowed']:
                raise ValueError("An analysis for this experiment is already queued or running.")
            if lif_path is None or lif_path.suffix.lower() != '.lif' or not lif_path.is_file():
                raise ValueError("The experiment entry must point to an existing Leica .lif file.")
            if not lif_candidates:
                raise ValueError(lif_error or "No usable FLIM series found in the LIF file.")
            selected_value = request.POST.get('LIF_Signal_Index', '').strip()
            if not selected_value:
                raise ValueError("Choose one of the detected LIF intensity time series.")
            selected_index = int(selected_value)
            selected = next(
                (row for row in lif_candidates if int(row['signal_index']) == selected_index),
                None,
            )
            if selected is None:
                raise ValueError("Choose one of the detected LIF intensity time series.")
            reference_time_value = request.POST.get('Segmentation_Time', '').strip()
            if not reference_time_value:
                raise ValueError("Choose the reference-image time index.")
            reference_time = int(reference_time_value)
            if not 0 <= reference_time < int(selected['reference_timepoints']):
                raise ValueError(
                    "Choose a reference time within the selected reference series "
                    f"(0..{int(selected['reference_timepoints']) - 1})."
                )
            entry.LIF_Signal_Index = selected_index
            entry.Cellpose_Model = (
                request.POST.get('Cellpose_Model', 'cpsam_v2').strip() or 'cpsam_v2'
            )
            if entry.Cellpose_Model not in {'cpsam_v2', 'cpsam', 'cpdino'}:
                raise ValueError(
                    "Choose a supported general Cellpose model "
                    "(cpsam_v2, cpsam, or cpdino)."
                )
            diameter = request.POST.get('Cellpose_Diameter', '').strip()
            entry.Cellpose_Diameter = float(diameter) if diameter else None
            if entry.Cellpose_Diameter is not None and (
                not math.isfinite(entry.Cellpose_Diameter) or entry.Cellpose_Diameter <= 0
            ):
                raise ValueError("Cellpose diameter must be a positive finite number or left blank.")
            for field in ('Segmentation_Time', 'Min_Cell_Area', 'Background_Ring'):
                value = int(request.POST.get(field, getattr(entry, field)))
                if value < 0:
                    raise ValueError(f"{field.replace('_', ' ')} cannot be negative.")
                setattr(entry, field, value)
            if entry.Background_Ring < 1:
                raise ValueError("Background ring width must be at least 1 pixel.")
            if entry.Min_Cell_Area < 1:
                raise ValueError("Minimum cell area must be at least 1 pixel.")
            max_area = request.POST.get('Max_Cell_Area', '').strip()
            entry.Max_Cell_Area = int(max_area) if max_area else None
            if entry.Max_Cell_Area is not None and entry.Max_Cell_Area < 1:
                raise ValueError("Maximum cell area must be at least 1 pixel.")
            if entry.Max_Cell_Area is not None and entry.Max_Cell_Area < entry.Min_Cell_Area:
                raise ValueError("Maximum cell area must be greater than or equal to minimum area.")
            entry.Analysis_Status = YFL.AnalysisStatus.QUEUED
            entry.Analysis_Error = ''
            entry.save()

            from django_q.tasks import async_task
            task_kwargs = {}
            task_timeout = getattr(settings, 'YEAST_FLIM_TASK_TIMEOUT', None)
            if task_timeout is not None:
                # A task running longer than the cluster 'retry' is delivered a second time.
                if int(getattr(settings, 'Q_CLUSTER', {}).get('retry', 0)) <= int(task_timeout):
                    raise ValueError(
                        "Q_CLUSTER['retry'] must be larger than YEAST_FLIM_TASK_TIMEOUT, "
                        "otherwise the analysis would be started twice."
                    )
                task_kwargs['timeout'] = int(task_timeout)
            try:
                from Analysis.scripts.Yeast_FLIM_Results import new_run_id, write_queued
                run_id = new_run_id()
                write_queued(entry, run_id)
                async_task('Analysis.scripts.Yeast_FLIM_Cellpose.run_yfl_analysis',
                           entry.pk, run_id, **task_kwargs)
            except Exception as exc:
                entry.Analysis_Status = YFL.AnalysisStatus.FAILED
                entry.Analysis_Error = f"Could not queue analysis: {exc}"
                entry.save(update_fields=['Analysis_Status', 'Analysis_Error'])
                raise
            return redirect('YFL_Analysis_View', pk=entry.pk)
        except Exception as exc:
            message = str(exc)

    selected_lif_index = None
    available_indices = {int(row['signal_index']) for row in lif_candidates}
    submitted_index = request.POST.get('LIF_Signal_Index', '').strip()
    if request.method == 'POST':
        if submitted_index.isdigit() and int(submitted_index) in available_indices:
            selected_lif_index = int(submitted_index)
    elif entry.LIF_Signal_Index in available_indices:
        selected_lif_index = entry.LIF_Signal_Index
    elif len(lif_candidates) == 1:
        selected_lif_index = int(lif_candidates[0]['signal_index'])
    selected_candidate = next(
        (
            row for row in lif_candidates
            if int(row['signal_index']) == selected_lif_index
        ),
        None,
    )
    if request.method == 'POST':
        reference_time_value = request.POST.get('Segmentation_Time', '').strip()
    elif entry.LIF_Signal_Index in available_indices:
        reference_time_value = entry.Segmentation_Time
    elif selected_candidate and int(selected_candidate['reference_timepoints']) == 1:
        reference_time_value = 0
    else:
        reference_time_value = None
    series_selection_required = (
        len(lif_candidates) > 1 and selected_lif_index is None
    )
    from Analysis.scripts.Yeast_FLIM_Results import live_status
    return render(request, 'Analysis_YFL.html', {
        'entry': entry,
        'live': live_status(entry),
        'message': message,
        'data_root': data_root,
        'lif_candidates': lif_candidates,
        'lif_error': lif_error,
        'selected_lif_index': selected_lif_index,
        'series_selection_required': series_selection_required,
        'reference_time_value': reference_time_value,
        'q_timeout': getattr(settings, 'YEAST_FLIM_TASK_TIMEOUT', None)
        or getattr(settings, 'Q_CLUSTER', {}).get('timeout'),
    })


def YFL_Dashboard_View(request, pk):
    """Interactive Yeast-FLIM results page (Plotly/Dash app 'YFL_Dashboard')."""
    from Analysis.scripts.Yeast_FLIM_Results import inspect_results

    entry = get_object_or_404(YFL, pk=pk)
    from Analysis.scripts.Yeast_FLIM_Results import live_status
    info = inspect_results(entry)
    return render(request, 'Analysis_YFL_Dashboard.html', {
        'entry': entry,
        'live': live_status(entry),
        'results_state': info['state'],
        'dash_context': {'entry-id': {'data': pk}},
    })


def YFL_Status_View(request, pk):
    """JSON status polled by the settings and results pages."""
    from Analysis.scripts.Yeast_FLIM_Results import live_status

    entry = get_object_or_404(YFL, pk=pk)
    response = JsonResponse(live_status(entry))
    response['Cache-Control'] = 'no-store'
    return response


def YFL_Download_View(request, pk, filename):
    """Serve one whitelisted YFL result artifact."""
    from django.http import FileResponse, Http404
    from Analysis.scripts.Yeast_FLIM_Results import DOWNLOADS, artifact_path

    entry = get_object_or_404(YFL, pk=pk)
    path = artifact_path(entry, filename)
    if path is None or not path.is_file():
        raise Http404("Artifact not found.")
    return FileResponse(path.open('rb'), as_attachment=True,
                        filename=f"YFL_{entry.pk}_{filename}",
                        content_type=DOWNLOADS[filename][1])

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

def MFP_Daily_View(request):
    # Einfach nur das neue Template laden!
    context = {
        'page_title': "MFP Daily Analysis",
    }
    return render(request, 'MFP_Daily_Dashboard.html', context)

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
