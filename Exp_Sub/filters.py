import django_filters as filters
from django.apps import apps

def get_Filter(ModelName):
    class Filter(filters.FilterSet):
        class Meta:
            model = apps.get_model('Exp_Sub', ModelName)
            exclude = ['']
    return Filter
