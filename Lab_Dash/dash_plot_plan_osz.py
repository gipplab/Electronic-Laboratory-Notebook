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
from Lab_Misc.models import OszScriptGen
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
from Analysis.Osz_Drop import *
from Lab_Misc import Load_Data
from Lab_Misc import General
from Lab_Misc.models import OszScriptGen


def conv(x):
    return x.replace(',', '.').encode()

def Gen_dash(dash_name):
    class Gen_fig():
        def load_data(self, target_id):
            try:
                entry = OszScriptGen.objects.get(id = target_id)
                self.entry = entry
                self.pump_df = pd.read_pickle(os.path.join(General.get_BasePath(), entry.Link_pump_df))
                self.gas_df = pd.read_pickle(os.path.join(General.get_BasePath(), entry.Link_gas_df))
                try:
                    self.temp_df = pd.read_pickle(os.path.join(General.get_BasePath(), entry.Link_temperatures_df))
                    return_str = 'Data loaded!'
                except:
                    return_str = 'Data loaded, no temperature found!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def Pump(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.pump_df['abs_time'], y=self.pump_df['flowrate_in']+ self.pump_df['flowrate_out'],
                        mode='markers + lines',
                        name='In + Out')
            )
            fig.add_trace(go.Scattergl(x=self.pump_df['abs_time'], y=self.pump_df['flowrate_in'],
                        mode='markers + lines',
                        name='In')
            )
            fig.add_trace(go.Scattergl(x=self.pump_df['abs_time'], y= self.pump_df['flowrate_out'],
                        mode='markers + lines',
                        name='Out')
            )
            fig.update_layout(  xaxis_title='Time [min]',
                                yaxis_title='Flowrate pump [muL/s]')
            return fig
            
        def Temp(self):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scattergl(x=self.pump_df['abs_time'], y=self.pump_df['flowrate_in']+ self.pump_df['flowrate_out'],
                        mode='markers + lines',
                        name='In + Out',),
                        secondary_y=False,
            )
            abs_times = [0]
            for item in self.temp_df['duration [min]']:
                curr_time = abs_times[-1]+item
                abs_times.append(curr_time)                
                abs_times.append(curr_time)
            abs_times = abs_times[:-1]
            temps=[]
            for i in range((int(len(abs_times)/2))):
                temps.append(self.temp_df.iloc[i]['temperature [°C]'])
                temps.append(self.temp_df.iloc[i]['temperature [°C]'])


            fig.add_trace(go.Scattergl(x=abs_times, y=temps,
                        mode='markers + lines',
                        name='Temperature',),
                        secondary_y=True,
            )
            
            fig.update_xaxes(title_text='Time [min]')
            fig.update_yaxes(title_text='Flowrate pump [muL/s]', secondary_y=False)
            fig.update_yaxes(title_text='Temperature[°C]', secondary_y=True)
            return fig

        def Gas(self):
            fig = go.Figure()
            for liquid in list(self.gas_df.columns.levels[0]):
                x_val = self.gas_df[liquid]['abs_time']
                y_val = self.gas_df[liquid]['flowrate']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers + lines',
                            name=liquid)
                )
            fig.update_layout(  xaxis_title='Time [min]',
                                yaxis_title='Flowrate gas [%]')
            return fig

        def Pump_Gas(self):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scattergl(x=self.pump_df['abs_time'], y=self.pump_df['flowrate_in']+ self.pump_df['flowrate_out'],
                        mode='lines+markers',
                        name='Pump'),
                        secondary_y=False,
            )
            for liquid in list(self.gas_df.columns.levels[0]):
                x_val = self.gas_df[liquid]['abs_time']
                y_val = self.gas_df[liquid]['flowrate']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='lines+markers',
                        name=liquid),
                        secondary_y=True,
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
                                                            options=[{'label': 'Pump:', 'value': 'Pump'},
                                                                        {'label': 'Temp:', 'value': 'Temp'},
                                                                        {'label': 'Gas:', 'value': 'Gas'},
                                                                        {'label': 'Pump_Gas:', 'value': 'Pump_Gas'},
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
        if Graph_select == 'Pump':
            fig = GenFig.Pump()
        elif Graph_select == 'Temp':
            fig = GenFig.Temp()
        elif Graph_select == 'Gas':
            fig = GenFig.Gas()
        elif Graph_select == 'Pump_Gas':
            fig = GenFig.Pump_Gas()
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
