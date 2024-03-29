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

app_name = 'Analysis'

urlpatterns = [
    #path("Comparisons/", views.Comparisons, name="Comparisons"),
    path("OszAnalysis/", views.OszAnalysis_view, name="OszAnalysis_view"),
    path("RSDAnalysis/", views.RSDAnalysis_view, name="RSDAnalysis_view"),
    path("DafAnalysis/", views.DafAnalysis_view, name="DafAnalysis_view"),
    path("GrvAnalysis/", views.GrvAnalysis_view, name="GrvAnalysis_view"),
    path("OszAnalysis_table/<str:pk>", views.OszAnalysis_table_view, name="OszAnalysis_table"),
    path("DafAnalysis/<str:pk>", views.DafAnalysis_table_view, name="DafAnalysis_table"),
    path('', views.index, name='index'),
]
