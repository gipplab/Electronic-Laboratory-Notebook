from django.shortcuts import render
import numpy as np
import os
import subprocess
from .Generate import CreateAndUpdate
import webbrowser
from django.templatetags.static import static
from django.shortcuts import redirect
from django.http import HttpResponse
from django.http import HttpResponseRedirect
#import Exp_Main.update_Exp as update_Exp
from django_tables2 import SingleTableView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from django.core.files.storage import default_storage
from .models import ExpPath
from .forms import get_Form
from .tables import get_Table
from .filters import get_Filter
from django.apps import apps

# Create your views here.
class Sub_table_view(SingleTableMixin, FilterView):
    def get_table_class(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        table_class = get_Table(model_name)
        return table_class

    def get_queryset(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        model = apps.get_model('Exp_Sub', model_name)
        return model.objects.all()

    def get_filterset_class(self, **kwargs):
        model_name = self.kwargs['Exp_name']
        filterset_class = get_Filter(model_name)
        return filterset_class
    table_pagination = {"per_page": 25}
    template_name = 'Show_sample.html'

class Sub_base_table_view(SingleTableMixin, FilterView):
    def get_table_class(self, **kwargs):
        model_name = 'ExpBase'
        table_class = get_Table(model_name)
        return table_class

    def get_queryset(self, **kwargs):
        model_name = 'ExpBase'
        model = apps.get_model('Exp_Sub', model_name)
        return model.objects.all()

    def get_filterset_class(self, **kwargs):
        model_name = 'ExpBase'
        filterset_class = get_Filter(model_name)
        return filterset_class
    table_pagination = {"per_page": 25}
    template_name = 'Show_sample.html'

def Generate(request):
    cwd = os.getcwd()
    Gen = CreateAndUpdate()
    if request.method == 'POST' and 'Generate_Names' in request.POST:
        Report_Path = Gen.Generate_Names()
        path = os.path.join(cwd, Report_Path)
        webbrowser.open_new(r'' + path)
    if request.method == 'POST' and 'Generate_Entries' in request.POST:
        Report_Paths = Gen.Generate_Entries()
        for Report_Path in Report_Paths:
            path = os.path.join(cwd, Report_Path)
            webbrowser.open_new(r'' + path)
    if request.method == 'POST' and 'ConnectFilesToExpMain' in request.POST:
        Report_Path = Gen.ConnectFilesToExpMain()
        path = os.path.join(cwd, Report_Path)
        webbrowser.open_new(r'' + path)
    return render(request = request,
                  template_name='Generate.html',)