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

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        def load_data(self, target_id):
            try:
                entry = SEL.objects.get(id = target_id)
                self.entry = entry
                file = os.path.join( rel_path, entry.Link_XLSX)
                df = pd.read_excel(file, 'Tabelle1')
                new_vals = df[df>1]/1000000#correct for wrong format
                Curr_Dash = self.entry.Dash
                df.update(new_vals)
                self.data = df
                self.data["Time (min.)"] = Curr_Dash.Start_datetime_elli + pd.TimedeltaIndex(self.data["Time (min.)"], unit='m')
                self.data["Time (min.)"] = self.data["Time (min.)"].dt.tz_convert(timezone.get_current_timezone())
                return_str = 'The following data could be loaded: Ellisometry'
                self.sub_data, return_str_sub = self.get_subs()
                return_str += return_str_sub
                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def has_sub(self):
            try:
                #Sub_Exp = self.entry.Sub_Exp.all()
                #print(Sub_Exp)
                #self.get_subs()
                return True
            except:
                return False

        def get_subs(self):
            Sub_Exps = self.entry.Sub_Exp.all()
            Sub_Exps_dic = {}
            return_str = ''
            for Sub_Exp in Sub_Exps:
                Device = Sub_Exp.Device
                model = apps.get_model('Exp_Sub', str(Device.Abbrev))
                Exp_in_Model = model.objects.get(id = Sub_Exp.id)
                if Device.Abbrev == 'MFL':
                    Gas = Exp_in_Model.Gas.first()
                    if Gas.Name == 'H2O':
                        MFL_H2O_data = self.get_sub_csv(Exp_in_Model)
                        MFL_H2O_data['Date_Time'] = pd.to_datetime(MFL_H2O_data['Date_Time'], format='%d.%m.%Y %H:%M:%S', errors="coerce")
                        MFL_H2O_data['Date_Time'] = MFL_H2O_data['Date_Time'].dt.tz_localize(timezone.get_current_timezone())
                        Sub_Exps_dic.update(MFL_H2O_data = MFL_H2O_data)
                        return_str += ', massflow of water stream'
                    if Gas.Name == 'N2':
                        MFL_N2_data = self.get_sub_csv(Exp_in_Model)
                        MFL_N2_data['Date_Time'] = pd.to_datetime(MFL_N2_data['Date_Time'], format='%d.%m.%Y %H:%M:%S', errors="coerce")
                        MFL_N2_data['Date_Time'] = MFL_N2_data['Date_Time'].dt.tz_localize(timezone.get_current_timezone())
                        Sub_Exps_dic.update(MFL_N2_data = MFL_N2_data)
                        return_str += ', massflow of nitrogen stream'
                if Device.Abbrev == 'HME':
                    for pos_env in Exp_in_Model.PossibleEnvironments:
                        if pos_env[0] == Exp_in_Model.Environments:
                            if pos_env[1] == 'Cell':
                                Humidity_data = self.get_sub_dbf(Exp_in_Model)
                                Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
                                Humidity_data['UHRZEIT'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
                                Sub_Exps_dic.update(HME_data = Humidity_data)
                                return_str += ', humidity measurements'
            return Sub_Exps_dic, return_str

        def get_sub_dbf(self, model):
            file = os.path.join( rel_path, model.Link)
            table = DBF(file, load=True)
            df = pd.DataFrame(iter(table))
            return df

        def get_sub_csv(self, model):
            file = os.path.join( rel_path, model.Link)
            #file_name = file[get_LastIndex(file, '\\')+1:get_LastIndex(file, '.')]
            df = pd.read_csv(file, sep=';', error_bad_lines=False, decimal = ',', parse_dates=[['Date', 'Time']])#skips bad lines
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
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['Time (min.)'], y=self.data['Thickness # 3'],
                        mode='markers',
                        name='CA left')
            )
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

        def Plot_3(self):
            Humidity_data = self.sub_data['HME_data']
            start_date = self.data['Time (min.)'][0]
            end_date = self.data['Time (min.)'][len(self.data)-1]
            date = start_date
            time_step = datetime.timedelta(seconds = 15)
            thickness = []
            humidities = []
            times  = []
            while(date<end_date):
                thicknes = np.mean(self.data['Thickness # 3'][(self.data['Time (min.)']<date+time_step)&(self.data['Time (min.)']>date)])
                thickness.append(thicknes)
                humidity = np.mean(Humidity_data['CHN1RH'][(Humidity_data['UHRZEIT']<date+time_step)&(Humidity_data['UHRZEIT']>date)])
                humidities.append(humidity)
                times.append(date)
                date = date + time_step
            self.cal_dat = pd.DataFrame(times, columns = ['times'])
            self.cal_dat["times"] = self.cal_dat["times"].dt.tz_convert('UTC')#time already shifted
            self.cal_dat ['thickness'] = thickness
            self.cal_dat ['humidities'] = humidities


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
                        mode='markers+text', marker={ 'color': 'rgba(0, 116, 217, 0.7)', 'size': 5 }, unselected={'marker': { 'color': 'rgba(200, 116, 0, 0.1)', 'size': 5 }, 'textfont': { 'color': 'rgba(0, 0, 0, 0)' }})

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