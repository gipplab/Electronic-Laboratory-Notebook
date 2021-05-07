from django import forms
from bootstrap_modal_forms.forms import BSModalForm
from .models import OCA, ExpBase, Observation
from django.apps import apps
from mptt.models import MPTTModel, TreeForeignKey

def get_Form(ModelName):
    class Form(BSModalForm):
        class Meta:
            model = apps.get_model('Exp_Main', ModelName)
            exclude = ['']
    return Form

class New_entry_form(BSModalForm):
    '''
    publication_date = forms.DateField(
        error_messages={'invalid': 'Enter a valid date in YYYY-MM-DD format.'}
    )
    '''

    class Meta:
        model = ExpBase
        exclude = ['']

class Observation_Form(BSModalForm):
    '''
    publication_date = forms.DateField(
        error_messages={'invalid': 'Enter a valid date in YYYY-MM-DD format.'}
    )
    '''

    class Meta:
        model = Observation
        exclude = ['']
