from django.shortcuts import render
import os
from .models import Project, ProjectEntry, OszScriptGen
from .tables import ProjectEntry as ProjectEntry_table
from .tables import Plan_Gas_OSZ as Plan_Gas_OSZ_table
from .forms import get_Form
import subprocess
import time
from django.apps import apps
from bootstrap_modal_forms.generic import (BSModalUpdateView)
from .gen_osz_scripts import *
from Lab_Misc import General
#import Lab_Misc.update_data as update_data
# Create your views here.

def index(request):
    return render(request = request, template_name='home.html')

# def update_samples(request):
#     if request.method == 'POST' and 'update_samples' in request.POST:
#         update_data.sample()
#     return render(request = request,
#                   template_name='update_samples.html',)

def projects(request):
    model = Project.objects.all()
    context = {'MttModel': model}
    context['table'] = ProjectEntry_table(ProjectEntry.objects.all())
    return render(request, 'Side_nav.html', context)

def projects_pk(request, pk):
    model = Project.objects.all()
    sel_obs = model.get(id = pk)

    context = {'MttModel': model}
    context['table'] = ProjectEntry_table(sel_obs.Entry.all())
    context['obs_pk'] = pk
    context['sel_obs'] = sel_obs
    context['data'] = ProjectEntry.objects.all()
    return render(request, 'Projects_single.html', context)

def Plan_Gas_OSZ(request):
    model = OszScriptGen.objects.all()
    context = {'MttModel': model}
    context['table'] = Plan_Gas_OSZ_table(model)
    return render(request, 'Plan_Gas_OSZ_table.html', context)

def Plan_Gas_OSZ_pk(request, pk):
    def gen_context():
        context = {'pk': pk}
        if len(entry.Link_pump_df) == 0:
            context['Has_df'] = False
        else:
            context['Has_df'] = True

        if len(entry.Link_folder_script) == 0:
            context['Has_Script'] = False
        else:
            context['Has_Script'] = True
        return context

    entry = OszScriptGen.objects.get(id = pk)
    if request.method == 'POST' and 'Run_Analysis' in request.POST:
        gen_scripts(pk)
        context = gen_context()
        return render(request, 'Plan_Gas_OSZ.html', context)
    if request.method == 'POST' and 'Open_Scripts' in request.POST:
        Folder_path = os.path.join(General.get_BasePath(), entry.Link_folder_script)
        Folder_path = Folder_path.replace(',', '","')
        subprocess.Popen(r'explorer /select,' + Folder_path)

    context = gen_context()
    return render(request, 'Plan_Gas_OSZ.html', context)


def Reports_file(request, File_Name):
    Html_Page = 'Reports/' + str(File_Name) + '.html'
    return render(request, Html_Page)
