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
            group_name = 'Exp_Main'
            model_name = 'SFG'
            curr_model = apps.get_model(group_name, model_name)
            exp_ids = Cur_Group.ExpBase.all().values_list('id', flat=True)
            i = 0
            data = []
            is_first = True
            for entry in SFG.objects.filter(id__in = exp_ids).order_by('Date_time'):
                file = os.path.join( rel_path, entry.Link)
                Sort_dict_t = {'Index': [i], 'x': entry.XPos_mm, 'y': entry.YPos_mm, 'Date_time': entry.Date_time, 'id': entry.id}
                Sort_dict_t = pd.DataFrame.from_dict(Sort_dict_t)
                data_t = pd.read_csv(file, sep='	', error_bad_lines=False, decimal = '.')#skips bad lines
                data_t.columns = ['Wavenumber', 'smth_1', 'smth_2', 'Signal']
                data_t['Index'] = i
                if is_first:
                    Sort_dict = Sort_dict_t
                    data = data_t
                    is_first = False
                else:
                    Sort_dict = Sort_dict.append(pd.DataFrame.from_dict(Sort_dict_t))
                    data = data.append(pd.DataFrame.from_dict(data_t))
                i+=1
            self.data = self.slice_data(data)
            self.Sort_dict = Sort_dict
            try:
                return_str = 'Data loaded!'

                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'

        def slice_data(self, data):
            curr_model = apps.get_model('Lab_Dash', self.entry.Dash.Typ)
            DashTab = curr_model.objects.get(Group_id = self.entry.Dash.pk)

            if isinstance(DashTab.Signal_high, float):
                slice_signal = data['Signal']<DashTab.Signal_high
                data = data[slice_signal]

            if isinstance(DashTab.Signal_low, float):
                slice_signal = data['Signal']>DashTab.Signal_low
                data = data[slice_signal]

            if isinstance(DashTab.Wavenumber_high, float):
                slice_wavenumber = data['Wavenumber']<DashTab.Wavenumber_high
                data = data[slice_wavenumber]

            if isinstance(DashTab.Wavenumber_low, float):
                slice_wavenumber = data['Wavenumber']>DashTab.Wavenumber_low
                data = data[slice_wavenumber]

            return data

        def Sort_time(self, replot = False):
            curr_model = apps.get_model('Lab_Dash', self.entry.Dash.Typ)
            DashTab = curr_model.objects.get(Group_id = self.entry.Dash.pk)
            fig = go.Figure()
            plot_distance = 0.3
            try:
                plot_distance = float(DashTab.Graph_distance)
            except:
                pass
            orderd = self.Sort_dict.sort_values(by ='Date_time')
            i = 0
            for row_id, cc_row in orderd.iterrows():
                data = self.data[self.data['Index']==cc_row['Index']]
                name_str = 'Loc id: ' + str(cc_row['Index']) + '  id: ' + str(cc_row['id'])
                fig.add_trace(go.Scattergl(x=data['Wavenumber'], y=data['Signal']+i*plot_distance,
                            mode='markers',
                            name=name_str)
                )
                i+=1
            fig.update_layout(  xaxis_title='Wavenumber [cm^-1]',
                                yaxis_title='Signal')
            return fig

        def Sort_x_y(self, replot = False):
            curr_model = apps.get_model('Lab_Dash', self.entry.Dash.Typ)
            DashTab = curr_model.objects.get(Group_id = self.entry.Dash.pk)
            fig = go.Figure()
            plot_distance = 0.3
            try:
                plot_distance = float(DashTab.Graph_distance)
            except:
                pass
            orderd = self.Sort_dict.sort_values(by = ['x', 'y'])
            i = 0
            for row_id, cc_row in orderd.iterrows():
                data = self.data[self.data['Index']==cc_row['Index']]
                name_str = str(cc_row['Index']) + ' x: ' + str(cc_row['x']) + '  y: ' + str(cc_row['y'])
                fig.add_trace(go.Scattergl(x=data['Wavenumber'], y=data['Signal']+i*plot_distance,
                            mode='markers',
                            name=name_str)
                )
                i+=1
            fig.update_layout(  xaxis_title='Wavenumber [cm^-1]',
                                yaxis_title='Signal')
            return fig

        def Sort_y_x(self, replot = False):
            curr_model = apps.get_model('Lab_Dash', self.entry.Dash.Typ)
            DashTab = curr_model.objects.get(Group_id = self.entry.Dash.pk)
            fig = go.Figure()
            plot_distance = 0.3
            try:
                plot_distance = float(DashTab.Graph_distance)
            except:
                pass
            orderd = self.Sort_dict.sort_values(by = ['x', 'y'])
            i = 0
            for row_id, cc_row in orderd.iterrows():
                data = self.data[self.data['Index']==cc_row['Index']]
                name_str = str(cc_row['Index']) + ' y: ' + str(cc_row['y']) + '  x: ' + str(cc_row['x'])
                fig.add_trace(go.Scattergl(x=data['Wavenumber'], y=data['Signal']+i*plot_distance,
                            mode='markers',
                            name=name_str)
                )
                i+=1
            fig.update_layout(  xaxis_title='Wavenumber [cm^-1]',
                                yaxis_title='Signal')
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
                                                            options=[{'label': 'Sort after time:', 'value': 'Sort_time'},
                                                                        {'label': 'Sort x, y:', 'value': 'Sort_x_y'},
                                                                        {'label': 'Sort y, x:', 'value': 'Sort_y_x'},
                                                                    ],
                                                            value='Sort_time',
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
        if Graph_select == 'Sort_time':
            fig = GenFig.Sort_time(replot)
        elif Graph_select == 'Sort_x_y':
            fig = GenFig.Sort_x_y(replot)
        elif Graph_select == 'Sort_y_x':
            fig = GenFig.Sort_y_x(replot)
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
