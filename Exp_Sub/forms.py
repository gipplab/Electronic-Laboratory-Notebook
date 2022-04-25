from django import forms
from bootstrap_modal_forms.forms import BSModalForm
from django.apps import apps
from mptt.models import MPTTModel, TreeForeignKey

def get_Form(ModelName):
    class Form(BSModalForm):
        class Meta:
            model = apps.get_model('Exp_Sub', ModelName)
            exclude = ['']
    return Form

