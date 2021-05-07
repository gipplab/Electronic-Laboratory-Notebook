from django import forms
from bootstrap_modal_forms.forms import BSModalForm
from .models import OCA
from mptt.models import MPTTModel, TreeForeignKey
from django.apps import apps

def get_Form(ModelName):
    class Form(forms.ModelForm):
        class Meta:
            model = apps.get_model('Lab_Dash', ModelName)
            exclude = ['']
    return Form
class OCAForm(BSModalForm):
    '''
    publication_date = forms.DateField(
        error_messages={'invalid': 'Enter a valid date in YYYY-MM-DD format.'}
    )
    '''

    class Meta:
        model = OCA
        exclude = ['']

def From_Choice(CHOICES):
    class select(forms.Form):
        field = forms.ChoiceField(choices=CHOICES)
    return select