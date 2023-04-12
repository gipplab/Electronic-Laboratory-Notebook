import json
import glob, os
import dash
import datetime
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
from django_plotly_dash import DjangoDash
from django.apps import apps
import plotly.graph_objects as go
from Lab_Misc.General import *
from dbfread import DBF
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
import numpy as np
import time
from Exp_Main.models import SEL
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
from Lab_Misc import General
from Analysis.SEL import SEL

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        def load_data(self, target_id):
            try:
                self.entry = SEL(target_id)
                self.entry.Merge_HIA()
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def Plot_3(self):
            data = self.entry.merged#[['time_loc', 'Thickness_Brush', 'RH_at_temp']].dropna()
            self.cal_dat = pd.DataFrame(data['time_loc'].to_list(), columns = ['times'])
            self.cal_dat["times"] = self.cal_dat["times"].dt.tz_convert('UTC')#time already shifted
            self.cal_dat ['thickness'] = data['Thickness_Brush']
            self.cal_dat ['humidities'] = data['RH_at_temp']


    def get_figure(df, x_col, y_col, selectedpoints, selectedpoints_local):

        if selectedpoints_local and selectedpoints_local['range']:
            ranges = selectedpoints_local['range']
            selection_bounds = {'x0': ranges['x'][0], 'x1': ranges['x'][1],
                                'y0': ranges['y'][0], 'y1': ranges['y'][1]}
        else:
            selection_bounds = {'x0': np.min(df[x_col]), 'x1': np.max(df[x_col]),
                                'y0': np.min(df[y_col]), 'y1': np.max(df[y_col])}

        # set which points are selected with the `selectedpoints` property
        # and style those points with the `selected` and `unselected`
        # attribute. see
        # https://medium.com/@plotlygraphs/notes-from-the-latest-plotly-js-release-b035a5b43e21
        # for an explanation
        fig = px.scatter(df, x=df[x_col], y=df[y_col], text=df.index)

        fig.update_traces(selectedpoints=selectedpoints, 
                        customdata=df.index,
                        mode='markers+text', marker={ 'color': 'rgba(0, 116, 217, 0.7)', 'size': 5 }, 
                        unselected={'marker': { 'color': 'rgba(200, 116, 0, 0.1)', 'size': 5 }, 'textfont': { 'color': 'rgba(0, 0, 0, 0)' }})

        fig.update_layout(margin={'l': 20, 'r': 0, 'b': 15, 't': 5}, dragmode='select', hovermode=False)

        fig.add_shape(dict({'type': 'rect', 
                            'line': { 'width': 1, 'dash': 'dot', 'color': 'darkgrey' }}, 
                        **selection_bounds))
        return fig


    value = 'temp'


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
        html.Div([
            html.Div(
                dcc.Graph(id='g1', config={'displayModeBar': True}),
                className='four columns',
                style={'width': '33%', 'display': 'inline-block'},
                ),
            html.Div(
                dcc.Graph(id='g2', config={'displayModeBar': True}),
                className='four columns',
                style={'width': '33%', 'display': 'inline-block'},
                ),
            html.Div(
                dcc.Graph(id='g3', config={'displayModeBar': True}),
                className='four columns',
                style={'width': '33%', 'display': 'inline-block'},
                )
            ], style={"display": "block"}, className='row'),
        dcc.Input(id='target_id', type='hidden', value='1'),
        html.Button('Load data', id='Load_Data'),
        dcc.Loading(
            id="loading",
            children=[html.Div([html.Div(id="loading-output")])],
            type="default",
        ),
    ])

    @app.callback(
        Output("loading-output", "children"),
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),])
    def update_output(n_clicks, target_id, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        if data_was_loaded:
            return_str += '\n Select the desired plot at the dropdown.'
        GenFig.Plot_3()
        return return_str
    # this callback defines 3 figures
    # as a function of the intersection of their 3 selections
    @app.callback(
        [Output('g1', 'figure'),
        Output('g2', 'figure'),
        Output('g3', 'figure')],
        [Input('target_id', 'value'),
        Input('g1', 'selectedData'),
        Input('g2', 'selectedData'),
        Input('g3', 'selectedData')]
        )
    def callback(target_id, selection1, selection2, selection3):
        no_data = True
        while no_data:
            try:
                GenFig.cal_dat
                no_data = False
            except:
                time.sleep(1)
        selectedpoints = GenFig.cal_dat.index
        for selected_data in [selection1, selection2, selection3]:
            if selected_data and selected_data['points']:
                selectedpoints = np.intersect1d(selectedpoints,
                    [p['customdata'] for p in selected_data['points']])

        return [get_figure(GenFig.cal_dat, "times", "thickness", selectedpoints, selection1),
                get_figure(GenFig.cal_dat, "times", "humidities", selectedpoints, selection2),
                get_figure(GenFig.cal_dat, "humidities", "thickness", selectedpoints, selection3)]