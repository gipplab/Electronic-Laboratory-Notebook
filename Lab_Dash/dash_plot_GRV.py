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
from Exp_Main.models import GRV
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
                entry = GRV.objects.get(id = target_id)
                self.entry = entry
                data = Load_Data.Load_from_Model('GRV', entry.id)
                self.data = data
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def CA_time(self):
            fig = go.Figure()
            data_set = self.data.columns.levels[0]

            for data_name in data_set:
                fig.add_trace(go.Scattergl(x=self.data[data_name]['frame'], y=(self.data[data_name]['transition']),
                            mode='markers',
                            name=data_name)
                )
            fig.add_trace(go.Scattergl(x=self.data[data_name]['frame'], y=(self.data[data_name]['shift_motor']),
                        mode='markers',
                        name='Motor')
            )
            fig.update_layout(  xaxis_title='Time [s]',
                                yaxis_title='Distance [mm]')
            return fig
        
        def CA_CLPos(self):
            fig = go.Figure()
            data_set = self.data.columns.levels[0]
            
            l_grv = [s for s in data_set if 'lower_in_groove' in s]
            if len(l_grv) == 2:
                l_grv = l_grv[0]
            try:
                zero = float(self.data[l_grv].tail(10).mean().loc[l_grv, 'transition'])
            except:
                zero = float(self.data[l_grv].tail(10).mean().loc['transition'])

            for data_name in data_set:
                fig.add_trace(go.Scattergl(x=self.data[data_name]['time'], y=(zero-self.data[data_name]['transition'])*self.entry.px_to_mm,
                            mode='markers',
                            name=data_name)
                )
            fig.update_layout(  xaxis_title='Time [s]',
                                yaxis_title='Distance [mm]')
            return fig

        def With_sub_data(self):
            fig = go.Figure()
            data_set = self.data.columns.levels[0]

            for data_name in data_set:
                fig.add_trace(go.Scattergl(x=self.data[data_name]['time'], y=(self.data[data_name]['Height_over_Bulk']),
                            mode='markers',
                            name=data_name)
                )
            fig.update_layout(  xaxis_title='Time [s]',
                                yaxis_title='Distance to bulk [mm]')
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
                                                            options=[{'label': 'RAW:', 'value': 'CA_time'},
                                                                        {'label': 'Profile:', 'value': 'CA/CL_Pos'},
                                                                        {'label': 'Vertical:', 'value': 'With_sub_data'},
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
