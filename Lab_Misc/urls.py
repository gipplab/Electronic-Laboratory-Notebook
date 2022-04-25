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

app_name = 'Lab_Misc'

urlpatterns = [
    #path("update_samples/", views.update_samples, name="update_samples"),
    path("Projects/", views.projects, name="projects"),
    path('Projects/<str:pk>', views.projects_pk, name='projects_pk'),
    path("Plan_Gas_OSZ/", views.Plan_Gas_OSZ, name="Plan_Gas_OSZ"),
    path('Plan_Gas_OSZ/<str:pk>', views.Plan_Gas_OSZ_pk, name='Plan_Gas_OSZ_pk'),
    path('Reports/<str:File_Name>', views.Reports_file, name='Reports_file'),
    path('', views.index, name='index'),
]
