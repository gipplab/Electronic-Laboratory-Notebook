import json
import glob, os
import dash
import datetime
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.io as pio
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
from Lab_Misc import General
from Exp_Main.models import SFG
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        def load_data(self, target_id):
            try:
                entry = SFG.objects.get(id = target_id)
                self.entry = entry
                file = os.path.join( rel_path, entry.Link)
                if file[-9:] == '_data.txt':
                    data = np.genfromtxt((conv(x) for x in open(file)), delimiter='	', skip_header=5, names=['Wellenzahl', 'smth_1', 'smth_2', 'Signal'])
                else:
                    data = np.genfromtxt(file, delimiter=',', skip_header=0, names=['Wellenzahl', 'Signal'])
                self.data = data
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'


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
                    Humidity_data = self.get_sub_dbf(Exp_in_Model)
                    Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
                    Humidity_data['UHRZEIT'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
                    Sub_Exps_dic.update(HME_data = Humidity_data)
                    return_str += ', humidity measurements'
                    self.has_sub = True
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

        def Wavenumber_Signal(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['Wellenzahl'], y=self.data['Signal'],
                        mode='markers',
                        name='CA left')
            )
            return fig

        def Compare_1924(self):
            entry = SFG.objects.get(id = 1924)
            file = os.path.join( rel_path, entry.Link)
            if file[-9:] == '_data.txt':
                data = np.genfromtxt((conv(x) for x in open(file)), delimiter='	', skip_header=5, names=['Wellenzahl', 'smth_1', 'smth_2', 'Signal'])
            else:
                data = np.genfromtxt(file, delimiter=',', skip_header=0, names=['Wellenzahl', 'Signal'])
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['Wellenzahl'], y=self.data['Signal'],
                        mode='markers',
                        name='Ethanol')
            )
            fig.add_trace(go.Scattergl(x=data['Wellenzahl'], y=data['Signal'],
                        mode='markers',
                        name='Water')
            )
            fig.update_layout(xaxis_title='Wavenumber [cm^-1]')

            fig.update_yaxes(title_text="Signal")

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
                                                            options=[{'label': 'Wavenumber / Signal', 'value': 'Wavenumber_Signal'},
                                                                        {'label': 'Compare to id 1924', 'value': 'Compare_1924'},
                                                                    ],
                                                            value='Wavenumber_Signal',
                                                            className='col-md-12',
                                                            ),
                                                ]),

        dcc.Input(id='target_id', type='hidden', value='1'),
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
        Output(component_id='example-graph', component_property='figure'),
        [Input('my-dropdown1', 'value')]
        )

    def update_figure(Graph_select, *args,**kwargs):
        global fig
        if Graph_select == 'Wavenumber_Signal':
            fig = GenFig.Wavenumber_Signal()
        elif Graph_select == 'Compare_1924':
            fig = GenFig.Compare_1924()
        return fig

    @app.callback(
        Output("loading-output", "children"),
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),])
    def update_output(n_clicks, target_id, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        if data_was_loaded:
            return_str += '\n Select the desired plot at the dropdown.'
        return return_str
