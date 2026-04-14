import django_filters as filters
from .models import OCA, CON, SEM, RLD, NEL, DIP, KUR, LQB, HEV, NAF, SFG, HED, ExpBase, Observation, ExpType
from Lab_Misc.models import ProjectEntry as Project
from django.apps import apps
from django.db import models
from django import forms
from django.utils.safestring import mark_safe

class CompactFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # JS & CSS Injektion: 100% Template-unabhängig
        injection = """
        <style>
        .compact-filter-form {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 15px !important;
            align-items: center !important;
            background-color: #f8f9fa !important;
            padding: 10px 15px !important;
            border-radius: 5px !important;
            border: 1px solid #dee2e6 !important;
            margin-bottom: 15px !important;
        }
        .compact-filter-form .form-group, 
        .compact-filter-form p, 
        .compact-filter-form > div,
        .compact-filter-form > * {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            margin-bottom: 0 !important;
            gap: 10px !important;
            text-align: left !important;
            
            /* FIX: Verhindert, dass Container 100% Breite erzwingen und umbrechen */
            width: auto !important;
            max-width: none !important;
            flex: 0 0 auto !important;
        }
        .compact-filter-form label {
            margin-bottom: 0 !important;
            font-weight: 600 !important;
            font-size: 0.9em !important;
            color: #495057 !important;
            white-space: nowrap !important;
            display: inline-block !important;
        }
        .compact-filter-form input, 
        .compact-filter-form select {
            max-width: 180px !important;
            min-width: 120px !important;
            width: auto !important;
            display: inline-block !important;
        }
        .compact-filter-form .controls,
        .compact-filter-form .form-group > div {
            display: flex !important;
            align-items: center !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .compact-filter-form button, 
        .compact-filter-form input[type="submit"] {
            margin-top: 0 !important;
        }
        </style>
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            var markers = document.querySelectorAll(".my-compact-filter");
            markers.forEach(function(marker) {
                var form = marker.closest("form");
                if (form) {
                    form.classList.add("compact-filter-form");
                    // Stellt sicher, dass auch alleinstehende Submit-Buttons in die Flex-Reihe geholt werden
                    var btns = form.querySelectorAll('button[type="submit"], a.btn');
                    btns.forEach(function(btn) {
                        var parent = btn.closest('p, div');
                        if (parent && parent.parentNode === form) {
                            parent.style.display = "inline-block";
                        }
                    });
                }
            });
        });
        </script>
        """

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control form-control-sm my-compact-filter'
            })
            
        if self.fields:
            first_key = list(self.fields.keys())[0]
            original_label = self.fields[first_key].label or first_key
            self.fields[first_key].label = mark_safe(injection + str(original_label))

CUSTOM_FILTER_OVERRIDES = {
    models.CharField: {
        'filter_class': filters.CharFilter,
        'extra': lambda f: {'lookup_expr': 'icontains'}
    },
    models.TextField: {
        'filter_class': filters.CharFilter,
        'extra': lambda f: {'lookup_expr': 'icontains'}
    },
    models.ManyToManyField: {
        'filter_class': filters.ModelChoiceFilter,
        'extra': lambda f: {'queryset': f.related_model.objects.all()}
    }
}

def get_Filter(ModelName):
    class Filter(filters.FilterSet):
        class Meta:
            model = apps.get_model('Exp_Main', ModelName)
            form = CompactFilterForm
            exclude = ['']
            filter_overrides = CUSTOM_FILTER_OVERRIDES
    return Filter

class ExpBase_filter(filters.FilterSet):
    Observation = filters.ModelChoiceFilter(queryset=Observation.objects.all())
    Project = filters.ModelChoiceFilter(queryset=Project.objects.all())
    Type = filters.ModelChoiceFilter(queryset=ExpType.objects.all())

    class Meta:
        model = ExpBase
        form = CompactFilterForm
        fields = ['Name', 'Sample_name', 'Device', 'Type', 'Observation', 'Project', 'Comment']
        filter_overrides = CUSTOM_FILTER_OVERRIDES

class OCA_filter(filters.FilterSet):
    class Meta:
        model = OCA
        form = CompactFilterForm
        exclude = [""]
        filter_overrides = CUSTOM_FILTER_OVERRIDES

class RLD_filter(filters.FilterSet):
    class Meta:
        model = RLD
        form = CompactFilterForm
        exclude = [""]
        filter_overrides = CUSTOM_FILTER_OVERRIDES
