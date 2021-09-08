import json
import glob, os
import dash
import plotly.io as pio
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
import datetime
from Exp_Main.models import SEL
from Exp_Sub.models import LSP
from Lab_Misc import Load_Data
from plotly.subplots import make_subplots
from Lab_Misc import General



def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        select_y1 = ['']
        select_y2 = ['']
        def load_data(self, target_id, ModelName):
            try:
                self.data = {}
                Model_Type = get_ModelOrigin(ModelName)
                if Model_Type == 'Exp_Main':
                    self.entry = get_in_full_model(target_id)
                if Model_Type == 'Exp_Sub':
                    self.entry = get_in_full_model_sub(target_id)
                self.data.update({self.entry.Name : Load_Data.Load_from_Model(ModelName, target_id)})
                return_str = 'The following data could be loaded: ' + self.entry.Name
                try:
                    self.data.update(Load_Data.get_subs_in_dic(target_id))
                except:
                    pass
                return True, return_str
            except:
                return False, 'No data found!'


        def sel_plot(self):
            try:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                for y1 in self.select_y1:
                    Exp_type = y1[:y1.index('||')]
                    col = y1[y1.index('||')+2:]
                    x_ax_sameModel = [item for item in self.select_x if Exp_type in item]
                    if len(x_ax_sameModel) == 0:
                        print('No x-axis for ' + Exp_type + ' was found')
                    else:
                        x_ax = x_ax_sameModel[0]
                        x_ax = x_ax[x_ax.index('||')+2:]
                        fig.add_trace(go.Scattergl(x=self.data[Exp_type][x_ax], y=self.data[Exp_type][col],
                                    mode='lines+markers',
                                    name=y1),
                                    secondary_y=False,
                        )
            except:
                pass
            for y2 in self.select_y2:
                try:
                    Exp_type = y2[:y2.index('||')]
                    col = y2[y2.index('||')+2:]
                    x_ax_sameModel = [item for item in self.select_x if Exp_type in item]
                    if len(x_ax_sameModel) == 0:
                        print('No x-axis for ' + Exp_type + ' was found')
                    else:
                        x_ax = x_ax_sameModel[0]
                        x_ax = x_ax[x_ax.index('||')+2:]
                        fig.add_trace(go.Scattergl(x=self.data[Exp_type][x_ax], y=self.data[Exp_type][col],
                                    mode='lines+markers',
                                    name=y2),
                                    secondary_y=True,
                        )
                except:
                    pass
            return fig


    value = 'temp'

    global fig
    app = DjangoDash(name=dash_name, id='target_id', model_name = 'ModelName')
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
    axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]

    app.layout = html.Div(children=[
        html.Div(id='Plot_sel_dropdown', children = [
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y1',
                value=['MTL', 'SF'],
                multi=True,
                style={'width': '25%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y2',
                value=['MTL', 'SF'],
                multi=True,
                style={'width': '25%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_x',
                value=['MTL', 'SF'],
                multi=True,
                style={'width': '25%', 'display': 'table-cell'},
            ),
            html.Button('Plot', id='Btn_Plot'),
        ], style={'width': '100%', 'display': 'flex', 'flex-direction': 'row'},),
        dcc.Input(id='target_id', type='hidden', value='1'),
        dcc.Input(id='ModelName', type='hidden', value='Dummy_Name'),
        html.Div(id='placeholder', style={'display': 'none'}),
        dcc.Graph(
            id='Sel_plot_graph',
            figure=fig,
        ),
        html.Button('Load data', id='Load_Data'),
        dcc.Loading(
            id="loading",
            children=[html.Div([html.Div(id="loading-output")])],
            type="default",
        ),
        html.Button('Save image', id='Btn_save_image'),
        html.Div(id='Save_output'),
    ])
    def save_fig():
        global fig
        fig.write_image("fig1.png", width=800, height=400, scale=10)

    @app.callback(
        Output(component_id='Save_output', component_property='children'),
        [Input('Btn_save_image', 'n_clicks'),],
    )
    def save_figure(n_clicks, *args,**kwargs):
        save_fig()
        return 'Image Saved!'

    @app.callback(
        Output(component_id='Sel_plot_graph', component_property='figure'),
        [Input('Btn_Plot', 'n_clicks')],
    )
    def update_figure_Sel_plot(n_clicks, *args,**kwargs):
        fig = GenFig.sel_plot()

        return fig

    @app.callback(
            Output(component_id='placeholder', component_property='style'),
            [Input('MS_drop_y1', 'value'),
            Input('MS_drop_y2', 'value'),
            Input('MS_drop_x', 'value'),]
            )
    def update_sel_list(select_y1, select_y2, select_x, *args,**kwargs):
        style={'display': 'none'}
        GenFig.select_y1 = select_y1
        GenFig.select_y2 = select_y2
        GenFig.select_x = select_x
        return style

    @app.callback(
        [Output(component_id='MS_drop_y1', component_property='options'),
        Output(component_id='MS_drop_y2', component_property='options'),
        Output(component_id='MS_drop_x', component_property='options'),
        Output("loading-output", "children"),],
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),
        Input('ModelName', 'value'),])
    def update_output(n_clicks, target_id, ModelName, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id, ModelName)
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data_name in GenFig.data:
                for col in GenFig.data[data_name]:
                    values = [data_name + '||' + col]*len(label_names)
                    axis_options.append(dict(zip(label_names, values)))
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
        return [axis_options, axis_options, axis_options, return_str]
