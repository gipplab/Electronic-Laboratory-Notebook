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
from django.shortcuts import render, redirect
from django.conf import settings

from .models import MFPAnalysis
from .scripts.MFP_Analyze import run_analysis
from Lab_Dash.models import MFP # Dein Experiment Model
from .scripts.MFP_Analyze import run_full_analysis



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

def index(request):
    # Wenn der Button gedrückt wurde
    if request.method == 'POST' and 'run_script' in request.POST:
        
        # 1. Läuft Jupyter schon?
        if not is_jupyter_running():
            print("--- Starte Jupyter Lab via start_analysis.sh ... ---")
            
            # Pfad zu deinem Skript zusammenbauen
            script_path = os.path.join(settings.BASE_DIR, 'start_analysis.sh')
            
            # Skript im Hintergrund starten (non-blocking)
            # Wir nutzen Popen statt os.system, damit Django nicht einfriert
            subprocess.Popen(['/bin/bash', script_path], cwd=settings.BASE_DIR)
            
            # Wir geben Jupyter 3 Sekunden Zeit zum Hochfahren
            time.sleep(3)
        else:
            print("--- Jupyter läuft bereits. Leite weiter ... ---")

        # 2. Weiterleitung zum Jupyter Lab
        return redirect("http://127.0.0.1:8888/lab")

    # Normaler Aufruf der Seite
    return render(request, 'Analysis.html')

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