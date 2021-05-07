from django import forms
from bootstrap_modal_forms.forms import BSModalForm
from mptt.models import MPTTModel, TreeForeignKey
from django.apps import apps

def get_Form(group_name, model_name):
    class Form(BSModalForm):
        class Meta:
            model = apps.get_model(group_name, model_name)
            exclude = ['']
    return Form
