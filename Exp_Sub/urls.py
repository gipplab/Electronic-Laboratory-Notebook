"""Webinterface URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
from . import views
from Exp_Sub.views import Sub_base_table_view, Sub_table_view

app_name = 'Exp_Sub'

urlpatterns = [
    path("", Sub_base_table_view.as_view(), name="Sub_base_table_view"),
    path(r"<str:Exp_name>/", Sub_table_view.as_view(), name="Sub_table_view"),
    path("Generate", views.Generate, name="Exp_Sub_Generate"),
]
