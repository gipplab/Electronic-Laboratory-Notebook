import json
import glob, os
import dash
import datetime
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
from django_plotly_dash import DjangoDash
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from Exp_Main.models import DAF
from plotly.subplots import make_subplots
from Analysis.Osz_Drop import *
from Lab_Misc import Load_Data
from Lab_Misc import General


def conv(x):
    return x.replace(',', '.').encode()

class Gen_fig():
    def __init__(self, target_id):
        entry = DAF.objects.get(id = target_id)
        self.entry = entry
        self.data = Load_Data.Load_from_Model('DAF', target_id)
        os.chdir(cwd)

    def CA_Time(self):
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=self.data['CA_L'],
                    mode='markers',
                    name='CA receding')
        )
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=self.data['CA_R'],
                    mode='markers',
                    name='CA advancing')
        )
        fig.update_layout(  xaxis_title='Time [sec]',
                            yaxis_title='Contact angle [°]')
        return fig

    def F_Time(self):
        fig = go.Figure()
        fig.update_layout(  xaxis_title='Time [sec]',
                            yaxis_title='Force [mu N]')
        try:
            y_val = 1000*self.data['force / mN']
        except:
            try:
                y_val = self.data['deflection / mm']
                fig.update_layout(yaxis_title='Deflection [mm]')
            except:
                y_val = self.data['deflection']
                fig.update_layout(yaxis_title='Deflection [pix]')
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=y_val,
                    mode='markers',
                    name='Force')
        )
        return fig

    def WL_Time(self):
        fig = go.Figure()
        fig.update_layout(  xaxis_title='Time [sec]',
                            yaxis_title='Drop Size [mm]')
        try:
            length = self.data['BI_right'] - self.data['BI_left']
            try:
                width = self.data['width / mm']
            except:
                pass
        except:
            length = self.data['contactpointright'] - self.data['contactpointleft']
            fig.update_layout(yaxis_title='Drop Size [pix]')
            try:
                width = self.data['P_width']
            except:
                pass
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=length,
                    mode='markers',
                    name='Drop Length')
        )
        try:
            fig.add_trace(go.Scattergl(x=self.data['Age'], y=width,
                        mode='markers',
                        name='Drop Width')
            )
        except:
            pass
        return fig

    def CL_pos_Time(self):
        fig = go.Figure()
        fig.update_layout(  xaxis_title='Time [sec]',
                            yaxis_title='CL Position [mm]')
        try:
            left = self.data['BI_left'] - self.data['BI_left'].to_numpy()[0]
            right = self.data['BI_right'] - self.data['BI_right'].to_numpy()[0]
        except:
            left = self.data['contactpointleft'] - self.data['contactpointleft'].to_numpy()[0]
            right = self.data['contactpointright'] - self.data['contactpointright'].to_numpy()[0]
            fig.update_layout(yaxis_title='CL Position [pix]')
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=left,
                    mode='markers',
                    name='CL left')
        )
        fig.add_trace(go.Scattergl(x=self.data['Age'], y=right,
                    mode='markers',
                    name='CL right')
        )
        return fig

value = 'temp'

app = DjangoDash(name='dash_plot_DAF', id='target_id')

cwd = os.getcwd()
rel_path = General.get_BasePath()

fig = fig = {
                'data': [{
                    'y': [1]
                }],
                'layout': {
                    'height': 800
                }
            }

app.layout = html.Div(children=[
    html.Div([dcc.Dropdown(id='my-dropdown1',
                                                           options=[{'label': 'Force / Time', 'value': 'F/Time'},
                                                                    {'label': 'CA / Time', 'value': 'CA/Time'},
                                                                    {'label': 'Drop Size / Time', 'value': 'WL/Time'},
                                                                    {'label': 'CL Position / Time', 'value': 'CL_pos/Time'},
                                                                   ],
                                                           value='F/Time',
                                                           className='col-md-12',
                                                          ),
                                              html.Div(id='test-output-div')
                                             ]),

    dcc.Input(id='target_id', type='hidden', value='1'),
    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

@app.expanded_callback(
    Output(component_id='example-graph', component_property='figure'),
    [Input(component_id='target_id', component_property='value'), 
    Input('my-dropdown1', 'value')]
    )

def update_figure(target_id, Graph_select, *args,**kwargs):
    GenFig = Gen_fig(target_id)

    if Graph_select == 'F/Time':
        fig = GenFig.F_Time()
    elif Graph_select == 'CA/Time':
        fig = GenFig.CA_Time()
    elif Graph_select == 'WL/Time':
        fig = GenFig.WL_Time()
    elif Graph_select == 'CL_pos/Time':
        fig = GenFig.CL_pos_Time()

    return fig
