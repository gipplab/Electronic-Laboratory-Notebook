"""Labbook URL Configuration

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
from django.contrib import admin
from django.urls import path, include
from Exp_Main import views as Exp_Main_views
from Exp_Main.views import Create_new_entry, Update_entry, Read_entry, Delete_entry, Samples_table_view
from Lab_Dash import dash_plot_SEL, dash_plot_SEL_compare, dash_plot_SFG
from Lab_Dash import dash_plot
from Lab_Dash.views import Update_dash

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('django_plotly_dash/', include('django_plotly_dash.urls')),
    path('', include('Lab_Misc.urls')),
    path('Dash/', include('Lab_Dash.urls')),
    #path(r"Exp/Samples/", Samples_table_view.as_view(), name="Samples_table_view"),
    path('Exp/', include('Exp_Main.urls')),
    path('ExpSub/', include('Exp_Sub.urls')),
    path('Analysis/', include('Analysis.urls')),
    path('create/<str:group>/<str:model>/<str:pk>', Create_new_entry.as_view(), name='create_entry'),
    path('update/<str:group>/<str:model>/<str:pk>', Update_entry.as_view(), name='update_entry'),
    path('update_Dash/<str:model><int:pk>', Update_dash.as_view(), name='update_dash'),
    path('read/<str:group>/<str:model>/<str:pk>', Read_entry.as_view(), name='read_entry'),
    path('delete/<str:group>/<str:model>/<str:pk>', Delete_entry.as_view(), name='delete_entry'),
    path("success/", Exp_Main_views.Success_return, name="Success_return"),
]#+ static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
