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
from django.conf.urls import url
from . import views
from Exp_Main.views import Samples_table_view, Exp_table_view, Prior_Exp
from Exp_Main.views import Create_new_entry, Update_entry, Read_entry, Delete_entry

app_name = 'Exp_Main'

urlpatterns = [
    path("success/", views.Success_return, name="Success_return"),
    #path("update_Exp/", views.update_Exp_view, name="update_Exp"),
    path("Observations/", views.observations, name="observations"),
    path("Comparisons/", views.Comparisons, name="Comparisons"),
    path("Groups/", views.groups, name="groups"),
    path("", Samples_table_view.as_view(), name="Samples_table_view"),
    path('Observations/<str:pk>', views.Observation_pk, name='Observation_pk'),
    path('Prior_Exp/<str:pk>', Prior_Exp.as_view(), name='Prior_Exp'),
    path('Groups/<str:pk>', views.group_pk, name='group_pk'),
    path(r"<str:Exp_name>/", Exp_table_view.as_view(), name="Exp_table_view"),
    path("Generate", views.Generate, name="Exp_Main_Generate"),
]
