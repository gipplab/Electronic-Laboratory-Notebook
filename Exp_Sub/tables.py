import django_tables2 as tables
from django_tables2_column_shifter.tables import ColumnShiftTable
from django.apps import apps

from django_tables2 import MultiTableMixin
from django.views.generic.base import TemplateView
from django_tables2 import A # alias for Accessor
import glob, os
#from django.utils.text import mark_safe

def get_Table(ModelName):
    class Table(ColumnShiftTable):
        change = tables.TemplateColumn(verbose_name= ('Edit'),
                                        template_name='Col_Edit_sub.html',
                                        orderable=False)

        class Meta:
            order_by = "Date_time"
            model = apps.get_model('Exp_Sub', ModelName)
            template_name = "django_tables2/bootstrap.html"
    return Table
