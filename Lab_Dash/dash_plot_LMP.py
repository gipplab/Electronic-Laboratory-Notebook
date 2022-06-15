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
from Exp_Main.models import LMP
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
from Analysis.Osz_Drop import *
from Lab_Misc import Load_Data
from Lab_Misc import General

def conv(x):
    return x.replace(',', '.').encode()

def Gen_dash(dash_name):
    class Gen_fig():
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]
        def load_data(self, target_id):
            try:
                entry = LMP.objects.get(id = target_id)
                self.entry = entry
                data = {}
                data['Mono'] = pd.read_csv(entry.lmpcosolventanalysis_set.first().Link_Hist_Mono)
                data['H2O'] = pd.read_csv(entry.lmpcosolventanalysis_set.first().Link_Hist_H2O)
                data['EtOH'] = pd.read_csv(entry.lmpcosolventanalysis_set.first().Link_Hist_EtOH)
                self.data = data
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def CA_time(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['Mono']['bins'], y=self.data['Mono']['counts'],
                        mode='markers',
                        name='counts')
            )
            fig.update_layout(  xaxis_title='Height',
                                yaxis_title='# Atoms')
            return fig

        def CA_CLPos(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['H2O']['bins'], y=self.data['H2O']['counts'],
                        mode='markers',
                        name='counts')
            )
            fig.update_layout(  xaxis_title='Height',
                                yaxis_title='# Atoms')
            return fig

        def With_sub_data(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['EtOH']['bins'], y=self.data['EtOH']['counts'],
                        mode='markers',
                        name='counts')
            )
            fig.update_layout(  xaxis_title='Height',
                                yaxis_title='# Atoms')
            return fig


    value = 'temp'

    global fig


    app = DjangoDash(name=dash_name, id='target_id')
    cwd = os.getcwd()
    rel_path = General.get_BasePath()
    GenFig = Gen_fig()
    fig = {
                'data': [{
                    'y': [1]
                }],
                'layout': {
                    'height': 800
                }
            }

    app.layout = html.Div(children=[
        html.Div([dcc.Dropdown(id='my-dropdown1',
                                                            options=[{'label': 'Monomers:', 'value': 'CA_time'},
                                                                        {'label': 'Ethanol:', 'value': 'CA/CL_Pos'},
                                                                        {'label': 'Water:', 'value': 'With_sub_data'},
                                                                    ],
                                                            value='Lineplot',
                                                            className='col-md-12',
                                                            ),
                                                ]),

        dcc.Input(id='target_id', type='hidden', value='1'),
        dcc.Input(id='path', type='hidden', value='1'),
        dcc.Graph(
            id='example-graph',
            figure=fig,
        ),
        html.Button('Load data', id='Load_Data'),
        dcc.Loading(
            id="loading",
            children=[html.Div([html.Div(id="loading-output")])],
            type="default",
        ),
    ])



    @app.callback(
        Output(component_id='example-graph', component_property='figure'),
        [Input('my-dropdown1', 'value')]
        )

    def update_figure(Graph_select, replot = False, *args, **kwargs):
        global fig
        if Graph_select == 'CA_time':
            fig = GenFig.CA_time()
        elif Graph_select == 'CA/CL_Pos':
            fig = GenFig.CA_CLPos()
        elif Graph_select == 'With_sub_data':
            fig = GenFig.With_sub_data()
        return fig

    @app.callback(
        Output("loading-output", "children"),
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),
        Input('path', 'value'),])

    def update_output(n_clicks, target_id, path, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        if data_was_loaded:
            return_str += '\n Select the desired plot at the dropdown.'
        return return_str
