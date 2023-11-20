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
from .views import Generic
from . import views

app_name = 'Lab_Dash'

urlpatterns = [
    path("Comparisons/<str:pk>", views.Comparison, name="Comparisons"),
    path("OszAnalysis/<str:pk>", views.OszAnalysis, name="OszAnalysis"),
    path("DafAnalysis/<str:pk>", views.DafAnalysis, name="DafAnalysis"),
    path("GrvAnalysis/<str:pk>", views.GrvAnalysis, name="GrvAnalysis"),
    path("update_model/<str:ModelName>/<str:pk>", views.update_model, name="update_model"),
    path("Generic/<str:ModelName>/<str:pk>", views.Generic, name="Generic"),
    path("Plan_Gas_OSZ/<str:pk>", views.Plan_Osz_graph, name="Plan_Gas_OSZ"),
    path("OCA/<str:pk>", views.OCA_graph, name="OCA_graph"),
    path("SFG/<str:pk>", views.SFG_graph, name="SFG_graph"),
    path("RSD/<str:pk>", views.RSD_Graph, name="RSD_Graph"),
    path("GRV/<str:pk>", views.GRV_Graph, name="GRV_Graph"),
    path("LMP/<str:pk>", views.LMP_Graph, name="LMP_Graph"),
    path("SEL/compare/<str:pk>", views.SEL_compare_graph, name="SEL_compare_graph"),
    path("SEL/compare_HIA/<str:pk>", views.SEL_compare_graph_HIA, name="SEL_compare_graph_HIA"),
    path("SEL/<str:pk>", views.SEL_graph, name="SEL_graph"),
    path("MFL/<str:pk>", views.MFL_graph, name="MFL_graph"),
    path("GRP/<str:model>/<str:pk>", views.GRP_graph, name="GRP_graph"),
    path("DAF/<str:pk>", views.DAF_graph, name="DAF_graph"),

]
