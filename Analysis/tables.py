import django_tables2 as tables
from .models import Comparison, OszAnalysisJoin
from .models import DafAnalysis
from django_tables2_column_shifter.tables import ColumnShiftTable
from django.apps import apps

from django_tables2 import MultiTableMixin
from django.views.generic.base import TemplateView
from django_tables2 import A # alias for Accessor
import glob, os
from Exp_Main.models import RSD
#from django.utils.text import mark_safe

def get_Table(ModelName):
    class Table(ColumnShiftTable):
        try:
            print(ColumnShiftTable.__getattribute__)
            
        except :
            print('error')

        class Meta:
            model = apps.get_model('Analysis', ModelName)
            template_name = "django_tables2/bootstrap.html"
    return Table

class Comparison_table(ColumnShiftTable):
    Link = tables.TemplateColumn(verbose_name= ('Link'),
                                    template_name='Col_Comparison.html',
                                    orderable=False)

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = Comparison
        template_name = "django_tables2/bootstrap.html"

class RSD_CA_Mess_table(ColumnShiftTable):
    Links = tables.TemplateColumn(verbose_name= ('Action Links'),
                                    template_name='Col_RSDAnalysis.html',
                                    orderable=False)

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = RSD
        template_name = "django_tables2/bootstrap.html"


class OszAnalysis_table(ColumnShiftTable):
    Link = tables.TemplateColumn(verbose_name= ('Link'),
                                    template_name='Col_OszAnalysis.html',
                                    orderable=False)

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = OszAnalysisJoin
        template_name = "django_tables2/bootstrap.html"


class DafAnalysis_table(ColumnShiftTable):
    Link = tables.TemplateColumn(verbose_name= ('Link'),
                                    template_name='Col_DafAnalysis.html',
                                    orderable=False)

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = DafAnalysis
        template_name = "django_tables2/bootstrap.html"
