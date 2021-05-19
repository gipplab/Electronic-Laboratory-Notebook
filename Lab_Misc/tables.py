import django_tables2 as tables
from .models import ProjectEntry, OszScriptGen
from django_tables2_column_shifter.tables import ColumnShiftTable

from django_tables2 import MultiTableMixin
from django.views.generic.base import TemplateView
from django_tables2 import A # alias for Accessor
import glob, os
#from django.utils.text import mark_safe

class ProjectEntry(ColumnShiftTable):

    '''change = tables.TemplateColumn(verbose_name= ('Edit'),
                                    template_name='Col_Edit.html',
                                    orderable=False)'''
    
    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = ProjectEntry
        template_name = "django_tables2/bootstrap.html"

class Plan_Gas_OSZ(ColumnShiftTable):
    change = tables.TemplateColumn(verbose_name= ('Edit'),
                                    template_name='Col_Edit_plan.html',
                                    orderable=False)
    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = OszScriptGen
        attrs = {"id": 'OszScriptGen'}
        template_name = "django_tables2/bootstrap.html"