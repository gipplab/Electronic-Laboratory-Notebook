from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
""" Automatically adding all Models of app to admin site
"""
app_models = apps.get_app_config('Lab_Dash').get_models()
for model in app_models:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass