from django.shortcuts import render
import os
from .models import Project, ProjectEntry
from .tables import ProjectEntry as ProjectEntry_table
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

def Reports_file(request, File_Name):
    Html_Page = 'Reports/' + str(File_Name) + '.html'
    return render(request, Html_Page)
