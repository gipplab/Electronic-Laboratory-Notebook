import django_filters as filters
from .models import OCA, CON, SEM, RLD, NEL, DIP, KUR, LQB, HEV, NAF, SFG, HED, ExpBase
from django.apps import apps

def get_Filter(ModelName):
    class Filter(filters.FilterSet):
        class Meta:
            model = apps.get_model('Exp_Main', ModelName)
            exclude = ['']
    return Filter
class ExpBase_filter(filters.FilterSet):
    Comment = filters.CharFilter(lookup_expr='icontains')
    class Meta:
        model = ExpBase
        exclude = [""]

class OCA_filter(filters.FilterSet):
    class Meta:
        model = OCA
        exclude = [""]

class RLD_filter(filters.FilterSet):
    class Meta:
        model = RLD
        exclude = [""]