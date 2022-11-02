from django.shortcuts import render
import os
import threading
from Analysis.Osz_Drop import Osz_Drop_Analysis
from Analysis.models import OszAnalysis, OszBaseParam, OszFitRes, OszAnalysisJoin, OszDerivedRes
from Analysis.models import DafAnalysis
from .tables import Comparison_table, OszAnalysis_table, get_Table, RSD_CA_Mess_table
from .tables import DafAnalysis_table
from Exp_Main.models import RSD, DAF

# Create your views here.
def index(request):
    #Osz_Drop_Analysis(4615)
    def start_jupyter():
        os.system('python manage.py shell_plus --notebook')
    if request.method == 'POST' and 'run_script' in request.POST:
        x = threading.Thread(target=start_jupyter)
        x.start()
    return render(request = request, template_name='Analysis.html')

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
        Osz_Drop_Analysis(OszAnalysis.objects.get(id = pk).Exp.id)
    return render(request, 'OszAnalysis_table.html', context)

def DafAnalysis_table_view(request, pk):
    model = DafAnalysis.objects.all()
    table = DafAnalysis_table(model)
    context = {'stuff': table}
    if request.method == 'POST' and 'Analyse_daf' in request.POST:
        # Daf_Analysis(DafAnalysis.objects.get(id = pk).Exp.id)
        pass
    return render(request, 'DafAnalysis_table.html', context)