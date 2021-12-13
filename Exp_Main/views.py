from django.shortcuts import render
import numpy as np
import os
from Lab_Misc import General
from Lab_Misc.General import *
from .Generate import CreateAndUpdate
import webbrowser
from itertools import chain
import threading
import subprocess
from Exp_Main import Sort_Videos
from django.templatetags.static import static
from django.shortcuts import redirect
from django.http import HttpResponse
from django.http import HttpResponseRedirect
#import Exp_Main.update_Exp as update_Exp
from django_tables2 import SingleTableView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from django.core.files.storage import default_storage
from .models import ExpPath, Group
from Analysis.models import Comparison
from .forms import New_entry_form
from .models import ExpBase, Observation, ObservationHierarchy
from Exp_Sub.models import ExpBase as ExpBaseSub
from Exp_Sub.models import ExpPath as ExpPathSub
from .models import OCA as OCA_model
from .models import RLD as RLD_model
from .tables import ExpBase_table, get_Table, Observation_table, Group_table, Comparison_table
from .filters import OCA_filter, RLD_filter, ExpBase_filter, get_Filter
from Lab_Misc.forms import get_Form
from .filters import *
from django.apps import apps
from django.urls import reverse_lazy
from bootstrap_modal_forms.generic import (BSModalLoginView,
                                           BSModalCreateView,
                                           BSModalUpdateView,
                                           BSModalReadView,
                                           BSModalDeleteView)

def index(request):
    return render(request, 'templates/albums.html')

def Success_return(request):
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))#redirects to previous url

def Comparisons(request):
    model = Comparison.objects.all()
    context = {'table': Comparison_table(model)}
    return render(request, 'Comparison.html', context)

def Generate(request):
    cwd = os.getcwd()
    Gen = CreateAndUpdate()
    if request.method == 'POST' and 'Generate_Names' in request.POST:
        Report_Path = Gen.Generate_Names()
        path = os.path.join(cwd, Report_Path)
        print(path)
        webbrowser.open_new(r'' + path)
    if request.method == 'POST' and 'Generate_Entries' in request.POST:
        try:
            Sort_Videos.Sort_RSD()
        except:
            pass
        try:
            Sort_Videos.Sort_CON()
        except:
            pass
        Report_Paths = Gen.Generate_Entries()
        for Report_Path in Report_Paths:
            path = os.path.join(cwd, Report_Path)
            print(path)
            webbrowser.open_new(r'' + path)
    if request.method == 'POST' and 'ConnectFilesToExpMain' in request.POST:
        Report_Path = Gen.ConnectFilesToExpMain()
        path = os.path.join(cwd, Report_Path)
        webbrowser.open_new(r'' + path)
    return render(request = request,
                  template_name='Generate.html',)

def Observation_pk(request, pk):
    model = ObservationHierarchy.objects.all()
    sel_obs = model.get(id = pk)

    context = {'Observations': model}
    context['table'] = Observation_table(sel_obs.Observation.all())
    context['obs_pk'] = pk
    context['sel_obs'] = sel_obs
    return render(request, 'observations_single.html', context)

def observations(request):
    model = ObservationHierarchy.objects.all()
    context = {'Observations': model}
    context['table'] = Observation_table(Observation.objects.all())
    return render(request, 'observations.html', context)

def group_pk(request, pk):
    model = Group.objects.all()
    sel_obs = model.get(id = pk)
    exp_ids = sel_obs.ExpBase.all().values_list('id', flat=True)
    context = {'Groups': model}
    table_class = get_Table('SFG')
    context['table'] = table_class(SFG.objects.filter(id__in = exp_ids))
    context['obs_pk'] = pk
    context['sel_obs'] = sel_obs
    return render(request, 'groups_single.html', context)

def groups(request):
    model = Group.objects.all()
    context = {'Groups': model}
    context['table'] = Group_table(Group.objects.all())
    return render(request, 'groups.html', context)

# def update_Exp_view(request):
#     if request.method == 'POST' and 'update_Exp' in request.POST:
#         get_old_DB = update_Exp.get_old_DB()
#         get_old_DB.set_Observation()
#     if request.method == 'POST' and 'Con_sub_Exp' in request.POST:
#         connect = update_Exp.connect_sub()
#         connect.LSP_OCA()
#     return render(request = request,
#                   template_name='update_Exp.html',)

class Exp_table_view(SingleTableMixin, FilterView):
    def get_table_class(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        table_class = get_Table(model_name)
        return table_class

    def get_queryset(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        model = apps.get_model('Exp_Main', model_name)
        return model.objects.all()

    def get_filterset_class(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        filterset_class = get_Filter(model_name)
        return filterset_class
    table_pagination = {"per_page": 50}
    template_name = 'Show_sample.html'

class Prior_Exp(SingleTableMixin, FilterView):
    def get_queryset(self, **kwargs):
        Main_id = self.kwargs['pk']
        queryset = ExpBase.objects.filter(Sample_name = ExpBase.objects.get(id = Main_id).Sample_name, 
                    Date_time__lte = ExpBase.objects.get(id = Main_id).Date_time)
        return queryset
    queryset = ExpBase.objects.filter(group__isnull = True)
    table = ExpBase_table(queryset)
    table_class = ExpBase_table
    table_pagination = {"per_page": 50}
    template_name = 'Show_sample.html'
    filterset_class = ExpBase_filter

class Samples_table_view(SingleTableMixin, FilterView):
    queryset = ExpBase.objects.filter(group__isnull = True)
    table = ExpBase_table(queryset)
    table_class = ExpBase_table
    table_pagination = {"per_page": 50}
    template_name = 'Show_sample.html'
    filterset_class = ExpBase_filter

class Create_new_entry(BSModalCreateView):
    template_name = 'Modal/create_entry.html'
    form_class = get_Form('Exp_Main', 'HED')
    def get_model_name(self, group_name, model_name, pk):
        if (model_name == 'None') & (group_name == 'Exp_Main'):
            curr_entry = ExpBase.objects.get(pk = pk)
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        elif (model_name == 'None') & (group_name == 'Exp_Sub'):
            curr_entry = ExpBaseSub.objects.get(pk = pk)
            curr_exp = ExpPathSub.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        else:
            name = model_name
        return name

    def get_form_class(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        formset_class = get_Form(group_name, model_name)
        return formset_class

    def get_queryset(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        curr_model = apps.get_model(group_name, model_name)
        self.curr_entry = curr_model.objects.get(pk = pk)
        queryset = curr_model.objects.all()
        return queryset
    success_message = 'Success: Book was created.'
    success_url = reverse_lazy('Success_return')


class Update_entry(BSModalUpdateView):
    model = ExpBase
    template_name = 'Modal/update_entry.html'
    form_class = get_Form('Exp_Main', 'OCA')
    def get_model_name(self, group_name, model_name, pk):
        if (model_name == 'None') & (group_name == 'Exp_Main'):
            curr_entry = ExpBase.objects.get(pk = pk)
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        elif (model_name == 'None') & (group_name == 'Exp_Sub'):
            curr_entry = ExpBaseSub.objects.get(pk = pk)
            curr_exp = ExpPathSub.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        else:
            name = model_name
        return name

    def get_form_class(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        formset_class = get_Form(group_name, model_name)
        return formset_class

    def get_queryset(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        curr_model = apps.get_model(group_name, model_name)
        self.curr_entry = curr_model.objects.get(pk = pk)
        queryset = curr_model.objects.all()
        return queryset

    success_message = 'Success: Book was updated.'
    success_url = reverse_lazy('Success_return')



class Read_entry(BSModalReadView):
    template_name = 'Modal/read_entry.html'
    curr_entry = ExpBase.objects.first()
    context_object_name = 'ExpBase'
    model = ExpBase

    def get_context_data(self,*args, **kwargs):
        context = super(Read_entry, self).get_context_data(*args,**kwargs)
        pk = self.kwargs['pk']
        entry = General.get_in_full_model(pk)
        if entry.Device.Abbrev == 'RSD':
            Drops = range(1,entry.Script.number_of_cycles+1) 
            Drop_names = ['All']
            for Drop in Drops:
                Drop_names.append('Drop_'+str(Drop))
            context['Drops'] = Drop_names
        return context

    def get_model_name(self, group_name, model_name, pk):
        if (model_name == 'None') & (group_name == 'Exp_Main'):
            curr_entry = ExpBase.objects.get(pk = pk)
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        elif (model_name == 'None') & (group_name == 'Exp_Sub'):
            curr_entry = ExpBaseSub.objects.get(pk = pk)
            curr_exp = ExpPathSub.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        else:
            name = model_name
        return name

    def template_path_exists(self, template_path):
        return default_storage.exists(os.path.join('Exp_Main/templates', template_path))

    def get_queryset(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        curr_model = apps.get_model(group_name, model_name)
        self.curr_entry = curr_model.objects.get(pk = pk)
        queryset = curr_model.objects.all()
        template_name = 'Modal/Experiments/' + str(model_name) + '.html'
        if str(model_name) == 'CON':
            template_name = 'Modal/Experiments/' + str(model_name) + '_.html'
        if self.template_path_exists(template_name):
            self.template_name = template_name
        return queryset

    def post(self, request, *args, **kwargs):
        def start_drop_ana():
            cwd = os.getcwd()
            path = 'Private\\Sessile.drop.analysis\\'
            subprocess.call(['python', 'Private/Sessile.drop.analysis/QT_sessile_drop_analysis.py', Link_to_vid, chosen_drop, path])
            os.chdir(cwd)
        def start_compress_vid():
            cwd = os.getcwd()
            subprocess.call(['python', 'Private/Sessile.drop.analysis/video_compression.py', Link_to_vid, chosen_drop, compression_level])
            os.chdir(cwd)
        pk = self.kwargs['pk']
        curr_entry = ExpBase.objects.get(pk = pk)
        curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
        curr_model = apps.get_model('Exp_Main', str(curr_exp.Abbrev))
        self.curr_entry = curr_model.objects.get(pk = pk)

        if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
            if request.method == 'POST' and 'OpenVideoPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link_Video)
                Folder_path = Folder_path.replace(',', '","')
                subprocess.Popen(r'explorer /select,' + Folder_path)

            if request.method == 'POST' and 'Run_compress_vid' in request.POST:
                chosen_drop=request.POST.get('Drop_choose')
                Link_to_vid = os.path.join(get_BasePath(), self.curr_entry.Link)
                compression_level = '1'
                x = threading.Thread(target=start_compress_vid)
                x.start()

            if request.method == 'POST' and 'Run_RSD_Analysis' in request.POST:
                chosen_drop=request.POST.get('Drop_choose')
                Link_to_vid = os.path.join(get_BasePath(), self.curr_entry.Link)
                self.curr_entry.Link_Data = self.curr_entry.Link.replace('01_Videos', '02_Analysis_Results')
                self.curr_entry.save()
                x = threading.Thread(target=start_drop_ana)
                x.start()
            
            if request.method == 'POST' and 'OpenMainPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                subprocess.Popen(r'explorer /select,' + Folder_path)

            if request.method == 'POST' and 'OpenPDFPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link_PDF)
                Folder_path = Folder_path.replace(',', '","')
                subprocess.Popen(r'explorer /select,' + Folder_path)

            if request.method == 'POST' and 'OpenDataPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link_Data)
                Folder_path = Folder_path.replace(',', '","')
                subprocess.Popen(r'explorer /select,' + Folder_path)

            if request.method == 'POST' and 'OpenXLSXPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link_XLSX)
                Folder_path = Folder_path.replace(',', '","')
                subprocess.Popen(r'explorer /select,' + Folder_path)
        else:
            if request.method == 'POST' and 'OpenVideoPath' in request.POST:
                Folder_path = os.path.join(self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponseRedirect('/Data/'+Folder_path)
            
            if request.method == 'POST' and 'OpenMainPath' in request.POST:
                Folder_path = os.path.join(self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponseRedirect('/Data/'+Folder_path)

            if request.method == 'POST' and 'ShowMainPath' in request.POST:
                Folder_path = os.path.join(get_BasePath(), self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponse('file:///' + OS_BasePath + Folder_path)

            if request.method == 'POST' and 'OpenPDFPath' in request.POST:
                Folder_path = os.path.join(self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponseRedirect('/Data/'+Folder_path)

            if request.method == 'POST' and 'OpenDataPath' in request.POST:
                Folder_path = os.path.join(self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponseRedirect('/Data/'+Folder_path)

            if request.method == 'POST' and 'OpenXLSXPath' in request.POST:
                Folder_path = os.path.join(self.curr_entry.Link)
                Folder_path = Folder_path.replace(',', '","')
                #subprocess.call(Folder_path)
                return HttpResponseRedirect('/Data/'+Folder_path)

        

        return HttpResponse('<script>history.back();</script>')



class Delete_entry(BSModalDeleteView):
    model = ExpBase
    def get_model_name(self, group_name, model_name, pk):
        if (model_name == 'None') & (group_name == 'Exp_Main'):
            curr_entry = ExpBase.objects.get(pk = pk)
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        elif (model_name == 'None') & (group_name == 'Exp_Sub'):
            curr_entry = ExpBaseSub.objects.get(pk = pk)
            curr_exp = ExpPathSub.objects.get(Name = str(curr_entry.Device))
            name = str(curr_exp.Abbrev)
        else:
            name = model_name
        return name
    def get_queryset(self, **kwargs):
        pk = self.kwargs['pk']
        model_name = self.kwargs['model']
        group_name = self.kwargs['group']
        model_name = self.get_model_name(group_name, model_name, pk)
        curr_model = apps.get_model(group_name, model_name)
        self.curr_entry = curr_model.objects.get(pk = pk)
        queryset = curr_model.objects.all()
        return queryset
    template_name = 'Modal/delete_entry.html'
    success_message = 'Success: Book was deleted.'
    success_url = reverse_lazy('Success_return')
