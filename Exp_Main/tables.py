import django_tables2 as tables
from .models import OCA, CON, SEM, RLD, NEL, DIP, KUR, LQB, HEV, NAF, SFG, HED, DAF, ExpBase, Observation, Group
from Analysis.models import Comparison
from django_tables2_column_shifter.tables import ColumnShiftTable
from django.apps import apps

from django_tables2 import MultiTableMixin
from django.views.generic.base import TemplateView
from django_tables2 import A # alias for Accessor
import glob, os
#from django.utils.text import mark_safe

def get_Table(ModelName):
    class Table(ColumnShiftTable):
        observation = tables.Column(verbose_name= ('Observation'), accessor='Observation')
        type_ = tables.Column(verbose_name= ('Type'), accessor='Type')
        change = tables.TemplateColumn(verbose_name= ('Edit'),
                                        template_name='Col_Edit.html',
                                        orderable=False)
        def render_observation(self, value, table):
          return ', '.join(l.Name for l in value.all())
        def render_type_(self, value, table):
          return ', '.join(l.Name for l in value.all())
        try:
            print(ColumnShiftTable.__getattribute__)
            
        except :
            print('error')

        class Meta:
            order_by = "Date_time"
            model = apps.get_model('Exp_Main', ModelName)
            template_name = "django_tables2/bootstrap.html"
    return Table

class Observation_table(ColumnShiftTable):

    '''change = tables.TemplateColumn(verbose_name= ('Edit'),
                                    template_name='Col_Edit.html',
                                    orderable=False)'''
    tree = tables.Column(verbose_name= ('Tree link'), accessor='observationhierarchy_set')
    exps = tables.Column(verbose_name= ('Connected experiments'), accessor='expbase_set')
    Link = tables.TemplateColumn(verbose_name= ('Link'),
                                    template_name='Col_Observations.html',
                                    orderable=False)
    def render_tree(self, value, table):
        links = []
        for item in value.all():
            link = '/'.join(l.Name for l in item.get_ancestors())
            if len(link) == 0:
                link = item.Name
            else:
                link += '/' + item.Name
            links.append(link)
        return ', '.join(l for l in links)
    def render_exps(self, value, table):
        return ', '.join(l.Name for l in value.all())

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = Observation
        template_name = "django_tables2/bootstrap.html"

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

class Group_table(ColumnShiftTable):

    '''change = tables.TemplateColumn(verbose_name= ('Edit'),
                                    template_name='Col_Edit.html',
                                    orderable=False)'''
    tree = tables.Column(verbose_name= ('Tree link'), accessor='Group_set')
    exps = tables.Column(verbose_name= ('Connected experiments'), accessor='expbase_set')
    Link = tables.TemplateColumn(verbose_name= ('Link'),
                                    template_name='Col_Groups.html',
                                    orderable=False)
    def render_tree(self, value, table):
        links = []
        for item in value.all():
            link = '/'.join(l.Name for l in item.get_ancestors())
            if len(link) == 0:
                link = item.Name
            else:
                link += '/' + item.Name
            links.append(link)
        return ', '.join(l for l in links)
    def render_exps(self, value, table):
        return ', '.join(l.Name for l in value.all())

    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        model = Group
        template_name = "django_tables2/bootstrap.html"
class ExpBase_table(ColumnShiftTable):
    observation = tables.Column(verbose_name= ('Observation'), accessor='Observation')
    group = tables.Column(verbose_name= ('Group'), accessor='group_set')
    type_ = tables.Column(verbose_name= ('Type'), accessor='Type')
    change = tables.TemplateColumn(verbose_name= ('Edit'),
                                    template_name='Col_Edit.html',
                                    orderable=False)
    def render_group(self, value, table):
        return ', '.join(l.Name for l in value.all())
    def render_observation(self, value, table):
        return ', '.join(l.Name for l in value.all())
    def render_type_(self, value, table):
        return ', '.join(l.Name for l in value.all())
    try:
        print(ColumnShiftTable.__getattribute__)
        
    except :
        print('error')

    class Meta:
        order_by = "Date_time"
        model = ExpBase
        attrs = {"id": 'ExpBase'}
        template_name = "django_tables2/bootstrap.html"