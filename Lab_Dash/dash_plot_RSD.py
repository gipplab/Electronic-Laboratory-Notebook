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
from Exp_Main.models import RSD
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
                entry = RSD.objects.get(id = target_id)
                self.entry = entry
                self.data = Load_Data.Load_sliced_RSD(target_id)
                self.Gas, self.Pump = Load_Data.Load_RSD_subs(target_id)
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def CA_time(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=(self.data['CA_L'] + self.data['CA_R'])/2,
                        mode='markers',
                        name='CA mean')
            )
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=self.data['CA_L'],
                        mode='markers',
                        name='CA left')
            )
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=self.data['CA_R'],
                        mode='markers',
                        name='CA right')
            )
            fig.update_layout(  xaxis_title='Time',
                                yaxis_title='Conact angle [°]')
            return fig

        def slice_residual(self):
            self.data['CA_L'] = self.data['CA_L'][self.data['res_left']>0.00001]
            self.data['CA_R'] = self.data['CA_R'][self.data['res_right']>0.00001]
            DashTab = self.entry.Dash
            if isinstance(DashTab.Residual, float):
                self.data['CA_L'] = self.data['CA_L'][self.data['res_left']<DashTab.Residual]
                self.data['CA_R'] = self.data['CA_R'][self.data['res_right']<DashTab.Residual]

        def CA_CLPos(self):
            fig = go.Figure()
            try:
                self.slice_residual()
            except:
                print('No residual found!')
            for i, drop in enumerate(list(self.data.index.unique(level=0))):
                dominant_gas_name = ''
                if len(self.Gas)>0:
                    first_time = self.data.loc[drop]['time_loc'].iloc[0]
                    last_time = self.data.loc[drop]['time_loc'].iloc[-1]
                    dominant_gas = 0
                    for gas in list(self.Gas.index.unique(level=0)):
                        curr_gas = self.Gas.loc[gas].where((self.Gas.loc[gas]['time_loc']<last_time)&(self.Gas.loc[gas]['time_loc']>first_time))
                        if curr_gas['sccm'].mean() > dominant_gas:
                            dominant_gas_name = gas
                            dominant_gas = curr_gas['sccm'].mean()
                x_val = self.data.loc[drop]['BI_left']
                y_val = self.data.loc[drop]['CA_L']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=drop+'_'+dominant_gas_name)
                )
                x_val = self.data.loc[drop]['BI_right']
                y_val = self.data.loc[drop]['CA_R']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=drop+'_'+dominant_gas_name)
                )
            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact angle [°]')
            return fig

        def With_sub_data(self):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=(self.data['CA_L'] + self.data['CA_R'])/2,
                        mode='markers',
                        name='CA mean'),
                        secondary_y=False,
            )
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=self.data['CA_L'],
                        mode='markers',
                        name='CA left'),
                        secondary_y=False,
            )
            fig.add_trace(go.Scattergl(x=self.data['abs_time'], y=self.data['CA_R'],
                        mode='markers',
                        name='CA right'),
                        secondary_y=False,
            )
            try:
                for gas in list(self.Gas.index.unique(level=0)):
                    x_val = self.Gas.loc[gas]['time_loc']
                    y_val = self.Gas.loc[gas]['ccm']
                    fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                                mode='markers',
                                name=gas),
                                secondary_y=True,
                    )
            except:
                print('No gas found!')

            for pump in list(self.Pump.index.unique(level=0)):
                x_val = self.Pump.loc[pump]['time_loc']
                y_val = self.Pump.loc[pump]['Current flow rate']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers + lines',
                            name=pump),
                            secondary_y=False,
                )


            fig.update_xaxes(title_text='Time [min]')
            fig.update_yaxes(title_text='Flowrate pump [muL/s]', secondary_y=False)
            fig.update_yaxes(title_text='Flowrate gas [%]', secondary_y=True)
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
                                                            options=[{'label': 'CA time:', 'value': 'CA_time'},
                                                                        {'label': 'CA / CL_Pos:', 'value': 'CA/CL_Pos'},
                                                                        {'label': 'With sub data:', 'value': 'With_sub_data'},
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
