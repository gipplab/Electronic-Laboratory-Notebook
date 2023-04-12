import json
import glob, os
from xml import dom
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
from Exp_Sub.models import LSP
from Analysis.Osz_Drop_RSD import Osz_Drop_Analysis as Osz_Drop_Analysis_RSD
from plotly.subplots import make_subplots
from Analysis.Osz_Drop import *
from Lab_Misc import Load_Data
from Lab_Misc import General
from Analysis.RSD import RSD

def conv(x):
    return x.replace(',', '.').encode()

def Gen_dash(dash_name):
    class Gen_fig():
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]
        def load_data(self, target_id):
            try:
                self.entry = RSD(target_id)
                self.entry.Merge_LSP_MFR()
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def CA_time(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_M'],
                        mode='markers',
                        name='CA mean')
            )
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_L'],
                        mode='markers',
                        name='CA left')
            )
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_R'],
                        mode='markers',
                        name='CA right')
            )
            fig.update_layout(  xaxis_title='Time',
                                yaxis_title='Conact angle [°]')
            return fig

        def CA_CLPos(self):
            fig = go.Figure()
            merged = self.entry.merged
            for i, drop in enumerate(merged['Drop_Number'].unique()):
                filtered = merged.loc[(merged['Drop_Number']==drop)]
                try:
                    dominant_gas_name = filtered['gas'].value_counts().idxmax()
                except:
                    dominant_gas_name = None
                label_name = 'Drop ' + str(drop)
                if dominant_gas_name != None:
                    label_name = label_name + ' ' + dominant_gas_name
                x_val = filtered['BI_left']
                y_val = filtered['CA_L']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
                x_val = filtered['BI_right']
                y_val = filtered['CA_R']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact angle [°]')
            return fig

        def CL_Speed(self):
            fig = go.Figure()
            merged = self.entry.merged
            for i, drop in enumerate(merged['Drop_Number'].unique()):
                filtered = merged.loc[(merged['Drop_Number']==drop)]
                try:
                    dominant_gas_name = filtered['gas'].value_counts().idxmax()
                except:
                    dominant_gas_name = None
                label_name = 'Drop ' + str(drop)
                if dominant_gas_name != None:
                    label_name = label_name + ' ' + dominant_gas_name
                x_val = filtered['BI_left']
                y_val = filtered['speed_left_avg']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
                x_val = filtered['BI_right']
                y_val = filtered['speed_right_avg']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact line speed [m/s]')
            return fig
        
        def CA_CLSpeed(self):
            fig = go.Figure()
            merged = self.entry.merged
            for i, drop in enumerate(merged['Drop_Number'].unique()):
                filtered = merged.loc[(merged['Drop_Number']==drop)]
                try:
                    dominant_gas_name = filtered['gas'].value_counts().idxmax()
                except:
                    dominant_gas_name = None
                label_name = 'Drop ' + str(drop)
                if dominant_gas_name != None:
                    label_name = label_name + ' ' + dominant_gas_name
                x_val = filtered['speed_left_avg']
                y_val = filtered['CA_L']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
                x_val = filtered['speed_right_avg']
                y_val = filtered['CA_R']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers',
                            marker=dict(color=self.colours[i]),
                            name=label_name)
                )
            fig.update_layout(  xaxis_title='Contact line speed [m/s]',
                                yaxis_title='Contact angle [°]')
            return fig

        def With_sub_data(self):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_M'],
                        mode='markers',
                        name='CA mean')
            )
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_L'],
                        mode='markers',
                        name='CA left')
            )
            fig.add_trace(go.Scattergl(x=self.entry.RSD_data['time_loc'], y=self.entry.RSD_data['CA_R'],
                        mode='markers',
                        name='CA right')
            )
            try:
                indices = [i for i, s in enumerate(list(self.entry.Sub_RSD_data)) if 'MFR' in s]
                for index in indices:
                    MFR_name = list(self.entry.Sub_RSD_data)[index]
                    gas_name = MFR_name[General.get_LastIndex(MFR_name,'_')+1:]
                    x_val = self.entry.Sub_RSD_data[MFR_name]['time_loc']
                    y_val = self.entry.Sub_RSD_data[MFR_name]['sccm']
                    fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                                mode='markers',
                                name=gas_name),
                                secondary_y=True,
                    )
            except:
                print('No gas found!')

            try:
                indices = [i for i, s in enumerate(list(self.entry.Sub_RSD_data)) if 'HIA' in s]
                for index in indices:
                    name = list(self.entry.Sub_RSD_data)[index]
                    x_val = self.entry.Sub_RSD_data[name]['time_loc']
                    y_val = self.entry.Sub_RSD_data[name]['Humidity:']
                    fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                                mode='markers + lines',
                                name=name),
                                secondary_y=False,
                    )
            except:
                print('No humidity found!')

            try:
                indices = [i for i, s in enumerate(list(self.entry.Sub_RSD_data)) if 'TCM' in s]
                for index in indices:
                    name = list(self.entry.Sub_RSD_data)[index]
                    x_val = self.entry.Sub_RSD_data[name]['time_loc']
                    y_val = self.entry.Sub_RSD_data[name]['object temperature']
                    fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                                mode='markers + lines',
                                name=name),
                                secondary_y=False,
                    )
            except:
                print('No temperature found!')

            indices = [i for i, s in enumerate(list(self.entry.Sub_RSD_data)) if 'LSP' in s]
            for index in indices:
                name = list(self.entry.Sub_RSD_data)[index]
                x_val = self.entry.Sub_RSD_data[name]['time_loc']
                y_val = self.entry.Sub_RSD_data[name]['Current flow rate']
                fig.add_trace(go.Scattergl(x=x_val, y=y_val,
                            mode='markers + lines',
                            name=name),
                            secondary_y=False,
                )


            fig.update_xaxes(title_text='Time [min]')
            fig.update_yaxes(title_text='Flowrate pump [muL/s]', secondary_y=False)
            fig.update_yaxes(title_text='Flowrate gas [%]', secondary_y=True)
            return fig


        def Analysis_plot(self):
            entry = General.get_in_full_model(self.entry.pk)
            if (entry.Link_Osz_join_LSP == None):# | (len(entry.Link_Osz_join_LSP) == 0):
                Osz_Drop_Analysis_RSD(entry.pk)
            elif (len(entry.Link_Osz_join_LSP) == 0):
                Osz_Drop_Analysis_RSD(entry.pk)
            rel_path = General.get_BasePath()
            data = pd.read_pickle(os.path.join(rel_path, entry.Link_Osz_join_LSP))
            Drop_parameters, Osz_fit_parameters, Derived_parameters = Load_Data.Load_OszAnalysis_in_df(entry.oszanalysis_set.first().id)
            fig = go.Figure()
            fig = self.fit_step('L', Drop_parameters, Osz_fit_parameters, data, fig)
            fig = self.fit_step('R', Drop_parameters, Osz_fit_parameters, data, fig)
            return fig

        def fit_step(self, L_or_R, Drop_parameters, Osz_fit_parameters, data, fig):
            if L_or_R == 'L':
                BI = 'BI_left Abs'
                CA = 'CA_L'
                RL = 'Left'
            if L_or_R == 'R':
                BI = 'BI_right'
                CA = 'CA_R'
                RL = 'Right'
            for Drop_Nr in Drop_parameters['General']['Drop_Nr']:
                if Drop_Nr==1:
                    pass
                else:
                    if Drop_Nr>2:
                        min_dia = abs(Drop_parameters.loc[Drop_parameters['General']['Drop_Nr'] == Drop_Nr-2, (RL, 'Max_CL')].iloc[0])
                    else:
                        min_dia = 0
                    Area_slice = (data['Drop_Number']==Drop_Nr)&(data['flowrate']>0)&(data[BI]>min_dia)
                    fit_drop = Osz_fit_parameters.loc[Osz_fit_parameters['General']['General']['Drop_Nr'] == Drop_Nr]
                    a, b, c, d = [fit_drop[RL]['Value']['Step_width'].item(), fit_drop[RL]['Value']['x_pos'].item(), 
                                    fit_drop[RL]['Value']['Step_hight'].item(), fit_drop[RL]['Value']['y_pos'].item()]
                    My_function=stufen_fit(data.loc[Area_slice, BI], a, b, c, d)
                    try:
                        x = np.arange(min_dia, max(data.loc[Area_slice, BI]), 0.01)
                    except:
                        x = np.arange(0, 0.1, 0.01)
                    i = Drop_Nr-1
                    if L_or_R == 'L':
                        fig.add_trace(go.Scatter(x=-data.loc[Area_slice, BI], y=data.loc[Area_slice, CA],
                                        mode='markers',
                                        marker=dict(color=self.colours[i]),
                                        name='Drop ' + str(Drop_Nr) + ' L')
                                    )
                        fig.add_trace(go.Scatter(x=-x, y=stufen_fit(x, a, b, c, d),
                                    mode='markers',
                                    marker=dict(color=self.colours[-i-1]),
                                    name='Drop ' + str(Drop_Nr) + ' L fit'),
                                )

                        fig.update_layout(  xaxis_title='Contact line position [mm]',
                                        yaxis_title='Contact angle [°]')
                    if L_or_R == 'R':
                        fig.add_trace(go.Scatter(x=data.loc[Area_slice, BI], y=data.loc[Area_slice, CA],
                                        mode='markers',
                                        marker=dict(color=self.colours[i]),
                                        name='Drop ' + str(Drop_Nr) + ' R')
                                    )
                        fig.add_trace(go.Scatter(x=x, y=stufen_fit(x, a, b, c, d),
                                    mode='markers',
                                    marker=dict(color=self.colours[-i-1]),
                                    name='Drop ' + str(Drop_Nr) + ' R fit'),
                                )

                        fig.update_layout(  xaxis_title='Contact line position [mm]',
                                        yaxis_title='Contact angle [°]')
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
                                                                        {'label': 'CL_Speed', 'value': 'CL_Speed'},
                                                                        {'label': 'CA / CL_Speed', 'value': 'CA_CLSpeed'},
                                                                        {'label': 'With sub data:', 'value': 'With_sub_data'},
                                                                        {'label': 'Analysis', 'value': 'Analysis'},
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
        elif Graph_select == 'CL_Speed':
            fig = GenFig.CL_Speed()
        elif Graph_select == 'CA_CLSpeed':
            fig = GenFig.CA_CLSpeed()
        elif Graph_select == 'With_sub_data':
            fig = GenFig.With_sub_data()
        elif Graph_select == 'Analysis':
            fig = GenFig.Analysis_plot()
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
