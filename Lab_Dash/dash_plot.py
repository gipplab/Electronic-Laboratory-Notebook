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
from Exp_Main.models import OCA
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
from Analysis.Osz_Drop import *
from Lab_Misc import Load_Data
from Lab_Misc import General


def conv(x):
    return x.replace(',', '.').encode()

class Gen_fig():
    drop_name = ['Drop 1', 'Drop 2', 'Drop 3', 'Drop 4', 'Drop 5', 'Drop 6', 'Drop 7', 'Drop 8', 'Drop 9', 'Drop 10', 'Drop 11', 'Drop 12', 'Drop 13', 'Drop 14', 'Drop 15',]
    colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]
    def __init__(self, target_id):
        entry = OCA.objects.get(id = target_id)
        self.entry = entry
        try:
            self.data = Load_Data.Load_sliced_OCA(target_id)
        except:
            print('slice failed')
            self.data = Load_Data.Load_from_Model('OCA', target_id)
        os.chdir(cwd)

    def has_sub(self):
        try:
            Sub_Exp = self.entry.Sub_Exp.all()
            print(Sub_Exp[0])
            return True
        except:
            return False

    def get_sub_lsp(self):
        Sub_Exps = self.entry.Sub_Exp.all()
        pks = []
        for Sub_Exp in Sub_Exps:
            if Sub_Exp.Device.id == 1:
                pks.append(Sub_Exp)
        if len(pks) == 0:
            print('no LSP found')
            return None
        elif len(pks) == 1:
            Syringe_pump = LSP.objects.get(pk = pks[0])
            file = os.path.join( rel_path, Syringe_pump.Link)
            df = pd.read_excel(file, 'Events record')
            return df
        else:
            print('Multiple LSPs assume coax needle exp')
            dfs = []
            for pk in pks:
                Syringe_pump = LSP.objects.get(pk = pk)
                file = os.path.join( rel_path, Syringe_pump.Link)
                df = pd.read_excel(file, 'Events record')
                dfs.append(df)
            df = dfs[0]
            df["Current flow rate"] = df["Current flow rate"] + dfs[1]["Current flow rate"]
            return df

    def slice_data(self, data):
        DashTab = self.entry.Dash
        if isinstance(DashTab.CA_high_degree, float):
            slice_CA_high = (data['CA_L']<DashTab.CA_high_degree) & (data['CA_R']<DashTab.CA_high_degree)
            data = data[slice_CA_high]

        if isinstance(DashTab.CA_low_degree, float):
            slice_CA_low = (data['CA_L']>DashTab.CA_low_degree) & (data['CA_R']>DashTab.CA_low_degree)
            data = data[slice_CA_low]

        if isinstance(DashTab.BD_high_mm, float):
            slice_BD = (data['BI_left']<DashTab.BD_high_mm) & (data['BI_right']<DashTab.BD_high_mm)
            data = data[slice_BD]

        if isinstance(DashTab.BD_low_mm, float):
            slice_BD = (data['BI_left']>DashTab.BD_low_mm) & (data['BI_right']>DashTab.BD_low_mm)
            data = data[slice_BD]

        if isinstance(DashTab.Time_high_sec, float):
            slice_time = data['Age']<DashTab.Time_high_sec
            data = data[slice_time]

        if isinstance(DashTab.Time_low_sec, float):
            slice_time = data['Age']>DashTab.Time_low_sec
            data = data[slice_time]
        return data

    def CA_Time(self):
        if max(self.data['Age']) > 600:
            Age = self.data['Age']/60
        else:
            Age = self.data['Age']
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_L'],
                    mode='markers',
                    name='CA left')
        )
        fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_R'],
                    mode='markers',
                    name='CA right')
        )
        fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_M'],
                    mode='markers',
                    name='CA average')
        )
        fig.update_layout(  xaxis_title='Time [sec]',
                            yaxis_title='Contact angle [°]')
        if max(self.data['Age']) > 600:
            fig.update_layout(  xaxis_title='Time [min]')
        return fig

    def CA_BD(self):
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=self.data['BD'], y=self.data['CA_L'],
                    mode='markers',
                    name='CA left')
        )
        fig.add_trace(go.Scattergl(x=self.data['BD'], y=self.data['CA_R'],
                    mode='markers',
                    name='CA right')
        )
        fig.add_trace(go.Scattergl(x=self.data['BD'], y=self.data['CA_M'],
                    mode='markers',
                    name='CA average')
        )
        fig.update_layout(  xaxis_title='Base diameter [mm]',
                            yaxis_title='Contact angle [°]')
        return fig

    def CA_RunNoo(self):
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=self.data['Run_No'], y=self.data['CA_L'],
                    mode='markers',
                    name='CA left')
        )
        fig.add_trace(go.Scattergl(x=self.data['Run_No'], y=self.data['CA_R'],
                    mode='markers',
                    name='CA right')
        )
        fig.add_trace(go.Scattergl(x=self.data['Run_No'], y=self.data['CA_M'],
                    mode='markers',
                    name='CA average')
        )
        fig.update_layout(  xaxis_title='Run number',
                            yaxis_title='Contact angle [°]')
        return fig

    def CA_RunNo(self):
        sub_data = self.get_sub_lsp()
        times = pd.to_datetime(sub_data["Event time"], format='%H:%M:%S,%f').dt.time
        time_pump = [time.hour*60*60+time.minute*60+time.second+time.microsecond/1000000 for time in times]
        flow_rate = sub_data["Current flow rate"]

        DashTab = self.entry.Dash
        time_to_add = 0

        if isinstance(DashTab.Time_diff_pump, float):
            time_to_add = DashTab.Time_diff_pump

        c = []
        i=0
        drop_name = ['Drop 1', 'Drop 2', 'Drop 3', 'Drop 4', 'Drop 5', 'Drop 6', 'Drop 7', 'Drop 8', 'Drop 9',
                'Drop 10', 'Drop 11', 'Drop 12', 'Drop 13', 'Drop 14', 'Drop 15',]
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]
        fig = go.Figure()

        if self.entry.Type.first().id == 7:#dispense mult
            time_pump = np.asarray(time_pump) + time_to_add
            slice_pump = (flow_rate==0)
            times_bigger_1 = time_pump[slice_pump]
            time_points = times_bigger_1[4::4]#[start_index:end_index:step]
            time_points = np.insert(time_points, 0, 0, axis=0)
            for i in range(len(time_points)-1):
                i += 1
                time_dif = 5
                slice_time = (self.data['Age'] > time_points[i-1]) & (self.data['Age'] < time_points[i])
                Time = self.data['Age'][slice_time]
                Dif_time = Time[0:-time_dif] - Time[time_dif:]
                CL_L = self.data['BI_left'][slice_time]
                CLS_L = CL_L[time_dif:] - CL_L[0:-time_dif]
                CLS_L = CLS_L/Dif_time
                CL_R = self.data['BI_right'][slice_time]
                CLS_R = CL_R[0:-time_dif] - CL_R[time_dif:]
                CLS_R = CLS_R/Dif_time

                fig.add_trace(go.Scatter(x=CL_L, y=CLS_L[time_dif:],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1]),
                            )
                fig.add_trace(go.Scatter(x=CL_R, y=CLS_R[time_dif:],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1])
                            )

            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact line speed [mm/s]')

        elif self.entry.Type.first().id == 13:#Oscillating drop
            time_pump = np.asarray(time_pump) + time_to_add
            slice_pump = (flow_rate<-1)
            times_bigger_1 = time_pump[slice_pump]
            time_points = times_bigger_1[1::2]#[start_index:end_index:step]
            time_points = np.insert(time_points, 0, 0, axis=0)
            for i in range(len(time_points)-1):
                i += 1
                time_dif = 10
                slice_time = (self.data['Age'] > time_points[i-1]) & (self.data['Age'] < time_points[i])
                Time = self.data['Age'][slice_time]
                Dif_time = Time - Time.shift(periods=time_dif)
                CL_L = self.data['BI_left'][slice_time]
                CLS_L = CL_L - CL_L.shift(periods=time_dif)
                CLS_L = CLS_L/Dif_time
                CL_R = self.data['BI_right'][slice_time]
                CLS_R = CL_R - CL_R.shift(periods=time_dif)
                CLS_R = CLS_R/Dif_time

                fig.add_trace(go.Scatter(x=CL_L, y=CLS_L[time_dif:],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1]),
                            )
                fig.add_trace(go.Scatter(x=CL_R, y=CLS_R[time_dif:],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1])
                            )

            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact line speed [mm/s]')
        return fig

    def CA_CLPos(self):
        sub_data = self.get_sub_lsp()
        times = pd.to_datetime(sub_data["Event time"], format='%H:%M:%S,%f').dt.time
        time_pump = [time.hour*60*60+time.minute*60+time.second+time.microsecond/1000000 for time in times]
        flow_rate = sub_data["Current flow rate"]

        DashTab = self.entry.Dash
        time_to_add = 0

        if isinstance(DashTab.Time_diff_pump, float):
            time_to_add = DashTab.Time_diff_pump

        c = []
        i=0
        drop_name = ['Drop 1', 'Drop 2', 'Drop 3', 'Drop 4', 'Drop 5', 'Drop 6', 'Drop 7', 'Drop 8', 'Drop 9',
                'Drop 10', 'Drop 11', 'Drop 12', 'Drop 13', 'Drop 14', 'Drop 15',]
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]
        fig = go.Figure()

        if self.entry.Type.first().id == 7:#dispense mult
            time_pump = np.asarray(time_pump) + time_to_add
            slice_pump = (flow_rate==0)
            times_bigger_1 = time_pump[slice_pump]
            time_points = times_bigger_1[4::4]#[start_index:end_index:step]
            time_points = np.insert(time_points, 0, 0, axis=0)
            for i in range(len(time_points)-1):
                i += 1
                slice_time = (self.data['Age'] > time_points[i-1]) & (self.data['Age'] < time_points[i])

                fig.add_trace(go.Scatter(x=self.data['BI_left'][slice_time], y=self.data['CA_L'][slice_time],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1]),
                            )
                fig.add_trace(go.Scatter(x=self.data['BI_right'][slice_time], y=self.data['CA_R'][slice_time],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1])
                            )

            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact angle [°]')

        elif self.entry.Type.first().id == 13:#Oscillating drop
            time_pump = np.asarray(time_pump) + time_to_add
            slice_pump = (flow_rate<-1)
            times_bigger_1 = time_pump[slice_pump]
            time_points = times_bigger_1[1::2]#[start_index:end_index:step]
            Sub_Exps = self.entry.Sub_Exp.all()
            pks = []
            for Sub_Exp in Sub_Exps:
                if Sub_Exp.Device.id == 1:
                    pks.append(Sub_Exp)
            if len(pks) == 2:
                zero_slice = (sub_data["Current flow rate"]<1)
                droptimes = time_pump[zero_slice]
                time_points = droptimes[4::4]
            time_points = np.insert(time_points, 0, 0, axis=0)
            diff_last_drop = time_points[-1]-self.data['Age'].iloc[-1]
            if abs(diff_last_drop) > 180:
                time_points = np.append(time_points, self.data['Age'].iloc[-1])
            for i in range(len(time_points)-1):
                i += 1
                if i>15:
                    continue
                slice_time = (self.data['Age'] > time_points[i-1]) & (self.data['Age'] < time_points[i])

                fig.add_trace(go.Scatter(x=self.data['BI_left'][slice_time], y=self.data['CA_L'][slice_time],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1]),
                            )
                fig.add_trace(go.Scatter(x=self.data['BI_right'][slice_time], y=self.data['CA_R'][slice_time],
                                mode='markers',
                                marker=dict(color=self.colours[i-1]),
                                name=self.drop_name[i-1])
                            )

            fig.update_layout(  xaxis_title='Contact line position [mm]',
                                yaxis_title='Contact angle [°]')
        return fig

    def Flow_Time(self):
        if self.has_sub():
            sub_data = self.get_sub_lsp()
            times = pd.to_datetime(sub_data["Event time"], format='%H:%M:%S,%f').dt.time
            time_pump = [time.hour*60*60+time.minute*60+time.second+time.microsecond/1000000 for time in times]
            flow_rate = sub_data["Current flow rate"]

            DashTab = self.entry.Dash
            time_to_add = 0

            if isinstance(DashTab.Time_diff_pump, float):
                time_to_add = DashTab.Time_diff_pump

            time_pump = np.asarray(time_pump) + time_to_add

            if max(self.data['Age']) > 600:
                Age = self.data['Age']/60
                time_pump = time_pump/60
            else:
                Age = self.data['Age']
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_L'],
                        mode='markers',
                        name='CA left'),
                        secondary_y=False,
            )
            fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_R'],
                        mode='markers',
                        name='CA right'),
                        secondary_y=False,
            )
            fig.add_trace(go.Scattergl(x=Age, y=self.data['CA_M'],
                        mode='markers',
                        name='CA average'),
                        secondary_y=False,
            )
            fig.add_trace(go.Scattergl(x=time_pump, y=flow_rate,
                        mode='markers+lines',
                        name='Pump'),
                        secondary_y=True,
            )
            fig.update_layout(xaxis_title='Time [sec]')

            fig.update_yaxes(title_text="Contact angle [°]", secondary_y=False)
            fig.update_yaxes(title_text="Flow rate [muL/min]", secondary_y=True)

            if max(self.data['Age']) > 600:
                fig.update_layout(  xaxis_title='Time [min]')
        else:
            fig = px.scatter(x=[1,2], y=[1,2])

        return fig

    def Analysis_plot(self):
        if (self.entry.Link_Osz_join_LSP == None) | (len(self.entry.Link_Osz_join_LSP) == 0):
            Osz_Drop_Analysis(self.entry.id)
        rel_path = General.get_BasePath()
        data = pd.read_pickle(os.path.join(rel_path, self.entry.Link_Osz_join_LSP))
        Drop_parameters, Osz_fit_parameters, Derived_parameters = Load_Data.Load_OszAnalysis_in_df(self.entry.oszanalysis_set.first().id)
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
                    Area_slice = (data['Drop_Nr']==Drop_Nr)&(data['Flowrate']>0)&(data[BI]>min_dia)
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
                                        name=self.drop_name[i] + ' L')
                                    )
                        fig.add_trace(go.Scatter(x=-x, y=stufen_fit(x, a, b, c, d),
                                    mode='markers',
                                    marker=dict(color=self.colours[-i-1]),
                                    name=self.drop_name[i] + ' L fit'),
                                )

                        fig.update_layout(  xaxis_title='Contact line position [mm]',
                                        yaxis_title='Contact angle [°]')
                    if L_or_R == 'R':
                        fig.add_trace(go.Scatter(x=data.loc[Area_slice, BI], y=data.loc[Area_slice, CA],
                                        mode='markers',
                                        marker=dict(color=self.colours[i]),
                                        name=self.drop_name[i] + ' R')
                                    )
                        fig.add_trace(go.Scatter(x=x, y=stufen_fit(x, a, b, c, d),
                                    mode='markers',
                                    marker=dict(color=self.colours[-i-1]),
                                    name=self.drop_name[i] + ' R fit'),
                                )

                        fig.update_layout(  xaxis_title='Contact line position [mm]',
                                        yaxis_title='Contact angle [°]')
            return fig

value = 'temp'

app = DjangoDash(name='dash_plot', id='target_id')

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
                                                           options=[{'label': 'CA / Time', 'value': 'CA/Time'},
                                                                    {'label': 'CA / Drop diameter', 'value': 'CA/BD'},
                                                                    {'label': 'CA / CL Position', 'value': 'CA/CL_Pos'},
                                                                    {'label': 'CA / Run number', 'value': 'CA/Run_no'},
                                                                    {'label': 'Flowrate / Time', 'value': 'Flow/Time'},
                                                                    {'label': 'Analysis', 'value': 'Analysis'},
                                                                   ],
                                                           value='CA/Time',
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

    if Graph_select == 'CA/Time':
        fig = GenFig.CA_Time()
    elif Graph_select == 'CA/BD':
        fig = GenFig.CA_BD()
    elif Graph_select == 'CA/Run_no':
        fig = GenFig.CA_RunNo()
    elif Graph_select == 'CA/CL_Pos':
        fig = GenFig.CA_CLPos()
    elif Graph_select == 'Flow/Time':
        fig = GenFig.Flow_Time()    
    elif Graph_select == 'Analysis':
        fig = GenFig.Analysis_plot()

    return fig
