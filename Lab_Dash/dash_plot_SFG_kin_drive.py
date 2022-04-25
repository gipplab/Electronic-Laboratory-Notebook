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
import plotly.express as px
from django.http import HttpResponse
from django.utils import timezone
import numpy as np
import datetime
from Exp_Main.models import Group
from Exp_Main.models import SFG
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
import pickle
from Lab_Misc import General

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        def init_load(self, target_id, path):
            self.save_path = path
            self.target_id = target_id
            path_to_Lineplot = os.path.join(self.save_path, 'Lineplot.pkl')
            if os.path.exists(path_to_Lineplot):
                record_time = os.path.getmtime(path_to_Lineplot)
                record_time = datetime.datetime.fromtimestamp(record_time)
                record_time = str(record_time.strftime('%d.%m.%Y %H:%M:%S'))
                self.Lineplot()
                return True, 'The plot was created at the ' + record_time
            else:
                return self.load_data(self.target_id)

        def load_data(self, target_id):
            Cur_Group = Group.objects.get(pk = target_id)
            self.entry = Cur_Group
            entry_first_m = Cur_Group.ExpBase.first()
            pk = entry_first_m.pk
            group_name = 'Exp_Main'
            model_name = 'SFG'
            curr_model = apps.get_model(group_name, model_name)
            entry_first = curr_model.objects.get(pk = pk)
            file = os.path.join( rel_path, entry_first.Link)
            df = pd.read_csv(file, sep="	",header=None, error_bad_lines=False)
            df.columns = ['Wavenumber', 'Signal']
            zeros = np.zeros(len(df))
            #ind = df[df['Wavenumber']=="Temperature: "].index[0]
            curr_time = 0
            is_first = True
            tim = []
            for entry_m in Cur_Group.ExpBase.all().order_by('Date_time'):
                try:
                    pk = entry_m.pk
                    entry = curr_model.objects.get(pk = pk)
                    file = os.path.join( rel_path, entry.Link)
                    int(file[get_LastIndex(file, '_')+1:get_LastIndex(file, '.')])
                    df = pd.read_csv(file, sep="	",header=None)
                    df.columns = ['Wavenumber', 'Signal']
                    df_raw = df
                    if is_first:
                        mess_time_sec = int(df_raw['Signal'][len(df_raw)-16][:df_raw['Signal'][len(df_raw)-16].find('.')])
                        accum = int(df_raw['Signal'][len(df_raw)-15][:df_raw['Signal'][len(df)-15].find('.')])
                        time_fac = mess_time_sec * accum
                    df['Wavenumber'] = pd.to_numeric(df['Wavenumber'], errors='coerce')
                    df['Signal'] = pd.to_numeric(df['Signal'], errors='coerce')
                    time_ser = zeros + curr_time*time_fac
                    time_ser = pd.DataFrame(time_ser)
                    df['Time'] = time_ser
                    df = df.iloc[:-21]
                    tim.append(curr_time*time_fac)
                    if is_first:
                        df = df.iloc[:-22]
                        self.waven = np.asarray(df['Wavenumber'])
                        data = df
                        is_first = False
                        z_surf = np.asarray(df['Signal'])
                    else:
                        df = df.iloc[:-21]
                        data = data.append(df)
                        z_surf = np.hstack((z_surf, np.asarray(df['Signal'])))
                    curr_time += 1
                except:
                    continue
            self.data = self.slice_data(data, True)
            self.surf = self.slice_data(data, False)
            #z_surf = z_surf.reshape(len(tim), len(self.waven))
            #self.z_surf = z_surf
            self.tim = np.asarray(tim)
            try:
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def slice_data(self, data, slice_signal):
            curr_model = apps.get_model('Lab_Dash', self.entry.Dash.Typ)
            DashTab = curr_model.objects.get(Group_id = self.entry.Dash.pk)

            if slice_signal:
                if isinstance(DashTab.Signal_high, float):
                    slice_signal = data['Signal']<DashTab.Signal_high
                    data = data[slice_signal]

                if isinstance(DashTab.Signal_low, float):
                    slice_signal = data['Signal']>DashTab.Signal_low
                    data = data[slice_signal]
            else:
                if isinstance(DashTab.Signal_high, float):
                    slice_signal = data['Signal']<DashTab.Signal_high
                    data[np.invert(slice_signal)] = DashTab.Signal_high

                if isinstance(DashTab.Signal_low, float):
                    slice_signal = data['Signal']>DashTab.Signal_low
                    data[np.invert(slice_signal)] = DashTab.Signal_low

            if isinstance(DashTab.Wavenumber_high, float):
                slice_wavenumber = data['Wavenumber']<DashTab.Wavenumber_high
                data = data[slice_wavenumber]
                slice_wavenumber = self.waven<DashTab.Wavenumber_high
                self.waven = self.waven[slice_wavenumber]

            if isinstance(DashTab.Wavenumber_low, float):
                slice_wavenumber = data['Wavenumber']>DashTab.Wavenumber_low
                data = data[slice_wavenumber]
                slice_wavenumber = self.waven>DashTab.Wavenumber_low
                self.waven = self.waven[slice_wavenumber]

            if isinstance(DashTab.Time_high_sec, float):
                slice_time = data['Time']<DashTab.Time_high_sec
                data = data[slice_time]
                slice_time = self.tim<DashTab.Time_high_sec
                self.tim = self.tim[slice_time]

            if isinstance(DashTab.Time_low_sec, float):
                slice_time = data['Time']>DashTab.Time_low_sec
                data = data[slice_time]
                slice_time = self.tim>DashTab.Time_low_sec
                self.tim = self.tim[slice_time]
            return data

        def Lineplot(self, replot = False):
            fig = go.Figure()
            path_to_Lineplot = os.path.join(self.save_path, 'Lineplot.pkl')
            if (os.path.exists(path_to_Lineplot)) & (replot == False):
                dat: pd.DataFrame = pd.read_pickle(path_to_Lineplot)
                fig = dat
            else:
                if not hasattr(self, 'data'):
                    self.load_data(self.target_id)
                fig.add_trace(go.Scatter3d(x=self.data["Wavenumber"], y=self.data["Time"], z=self.data["Signal"],
                    mode = 'lines',
                    line=dict(
                        color=self.data["Signal"],
                        colorscale='Viridis',
                        width=2
                    )
                ))
                fig.update_layout(scene = dict(
                    xaxis_title='Wave number',
                    yaxis_title='Time [sec]',
                    zaxis_title='Signal'))
                if not os.path.exists(self.save_path):
                    os.makedirs(self.save_path)
                with open(path_to_Lineplot,"wb") as f:
                    pickle.dump(fig, f)
            return fig

        def Surfaceplot(self, replot = False):
            fig = go.Figure()
            path_to_Surfaceplot = os.path.join(self.save_path, 'Surfaceplot.pkl')
            if (os.path.exists(path_to_Surfaceplot)) & (replot == False):
                dat: pd.DataFrame = pd.read_pickle(path_to_Surfaceplot)
                fig = dat
            else:
                data = getattr(self, "surf", None)
                if not callable(data):
                    self.load_data(self.target_id)
                z_surf = np.asarray(self.surf["Signal"])
                z_surf = z_surf.reshape(len(self.tim), len(self.waven))
                fig = go.Figure(data=[go.Surface(z=z_surf, y=self.tim, x=self.waven)])
                #fig.write_html("dash_save.html")
                fig.update_layout(scene = dict(
                    xaxis_title='Wave number',
                    yaxis_title='Time [sec]',
                    zaxis_title='Signal'))
                if not os.path.exists(self.save_path):
                    os.makedirs(self.save_path)
                with open(path_to_Surfaceplot,"wb") as f:
                    pickle.dump(fig, f)
            return fig

    value = 'temp'

    global fig
    global Redraw_clicked
    Redraw_clicked = 0


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
                                                            options=[{'label': 'Lineplot:', 'value': 'Lineplot'},
                                                                        {'label': 'Surfaceplot:', 'value': 'Surfaceplot'},
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
        html.Button('Save image', id='Btn_save_image'),
        html.Div(id='Save_output'),
        html.Button('Redraw graph', id='Btn_redraw_graph'),
        html.Div(id='Redraw_graph_output'),
    ])

    def save_fig():
        global fig
        fig.write_image("fig1.png", width=800, height=400, scale=10)

    @app.callback(
    Output(component_id='Redraw_graph_output', component_property='children'),
    [Input('Btn_redraw_graph', 'n_clicks'),
    Input('my-dropdown1', 'value'),],
    )
    def redraw_graph(n_clicks, Graph_select, *args,**kwargs):
        global Redraw_clicked
        if n_clicks > Redraw_clicked:
            update_figure(Graph_select, True)
            Redraw_clicked = n_clicks
            return 'Graph was redrawn! Refresh page!'
        else:
            return 'Old graph was used!'

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

    def update_figure(Graph_select, replot = False, *args, **kwargs):
        global fig
        if Graph_select == 'Lineplot':
            fig = GenFig.Lineplot(replot)
        elif Graph_select == 'Surfaceplot':
            fig = GenFig.Surfaceplot(replot)
        return fig

    @app.callback(
        Output("loading-output", "children"),
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),
        Input('path', 'value'),])

    def update_output(n_clicks, target_id, path, *args,**kwargs):
        data_was_loaded, return_str = GenFig.init_load(target_id, path)
        if data_was_loaded:
            return_str += '\n Select the desired plot at the dropdown.'
        return return_str
