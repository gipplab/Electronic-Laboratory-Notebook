from django import forms
from bootstrap_modal_forms.forms import BSModalForm
from django.db.models import fields
from mptt.models import MPTTModel, TreeForeignKey
from django.apps import apps
from Lab_Misc.models import SampleBase

def get_Form(group_name, model_name):
    class Form(BSModalForm):
        class Meta:
            model = apps.get_model(group_name, model_name)
            exclude = ['']
    return Form

class Samples(BSModalForm):
    class Meta:
        model = SampleBase
        fields = ['Name']
