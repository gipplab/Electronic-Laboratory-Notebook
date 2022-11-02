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
from plotly.subplots import make_subplots
from Lab_Misc import Load_Data



def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name):
    class Gen_fig():
        select_y1 = ['']
        select_y2 = ['']
        def load_data(self, target_id):
            try:
                entry = SEL.objects.get(id = target_id)
                self.entry = entry
                df = Load_Data.Load_from_Model('SEL', target_id)
                self.data = {}
                self.data.update(Ellipsometry = df)
                return_str = 'The following data could be loaded: Ellisometry'
                self.data.update(Load_Data.get_subs_in_dic(target_id))
                os.chdir(cwd)
                return True, return_str
            except:
                return False, 'No data found!'


        def get_subs(self):
            Sub_Exps = self.entry.Sub_Exp.all()
            return_str = ''
            for Sub_Exp in Sub_Exps:
                Device = Sub_Exp.Device
                model = apps.get_model('Exp_Sub', str(Device.Abbrev))
                Exp_in_Model = model.objects.get(id = Sub_Exp.id)
                if Device.Abbrev == 'MFR':
                    MFR_data = Load_Data.Load_from_Model('MFR', Sub_Exp.id)
                    self.data.update(MFR_H2O_data = MFR_data)
                    return_str += ', massflow RS232 of water stream'
                if Device.Abbrev == 'MFL':
                    Gas = Exp_in_Model.Gas.first()
                    if Gas.Name == 'H2O':
                        MFL_H2O_data = Load_Data.Load_from_Model('MFL', Sub_Exp.id)
                        self.data.update(MFL_H2O_data = MFL_H2O_data)
                        return_str += ', massflow of water stream'
                    if Gas.Name == 'N2':
                        MFL_N2_data = Load_Data.Load_from_Model('MFL', Sub_Exp.id)
                        self.data.update(MFL_N2_data = MFL_N2_data)
                        return_str += ', massflow of nitrogen stream'
                if Device.Abbrev == 'HME':
                    if Exp_in_Model.Environments == '1':
                        Humidity_data = Load_Data.Load_from_Model('HME', Sub_Exp.id)
                        self.data.update(HME_cell = Humidity_data)
                        return_str += ', humidity measurements of the cell'
                        self.has_sub = True
                    if Exp_in_Model.Environments == '2':
                        Humidity_data = Load_Data.Load_from_Model('HME', Sub_Exp.id)
                        self.data.update(HME_data_room = Humidity_data)
                        return_str += ', humidity measurements of the room'
                        self.has_sub = True
            return return_str

        def CA_Time(self):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=self.data['Ellipsometry']['time'], y=self.data['Ellipsometry']['Thickness_Brush'],
                        mode='markers',
                        name='CA left')
            )
            return fig

        def sel_plot(self):
            try:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                for y1 in self.select_y1:
                    Exp_type = y1[:y1.index('-')]
                    col = y1[y1.index('-')+1:]
                    fig.add_trace(go.Scattergl(x=self.data[Exp_type]['time_loc'], y=self.data[Exp_type][col],
                                mode='markers',
                                name=y1),
                                secondary_y=False,
                    )
            except:
                pass
            for y2 in self.select_y2:
                try:
                    Exp_type = y2[:y2.index('-')]
                    col = y2[y2.index('-')+1:]
                    fig.add_trace(go.Scattergl(x=self.data[Exp_type]['time_loc'], y=self.data[Exp_type][col],
                                mode='markers',
                                name=y2),
                                secondary_y=True,
                    )
                except:
                    pass
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

        def CA_RunNo(self):
            Humidity_data = self.data['HME_cell']
            start_date = self.data['Ellipsometry']['time'][0]
            end_date = self.data['Ellipsometry']['time'][len(self.data['Ellipsometry'])-1]
            date = start_date
            time_step = datetime.timedelta(seconds = 15)
            thickness = []
            humidities = []
            while(date<end_date):
                thicknes = np.mean(self.data['Ellipsometry']['Thickness_Brush'][(self.data['Ellipsometry']['time']<date+time_step)&(self.data['Ellipsometry']['time']>date)])
                thickness.append(thicknes)
                humidity = np.mean(Humidity_data['Humidity'][(Humidity_data['time']<date+time_step)&(Humidity_data['time']>date)])
                humidities.append(humidity)
                date = date + time_step
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=humidities, y=thickness,
                        mode='markers',
                        name='Data')
            )
            fig.update_layout(  xaxis_title='Humidity [%]',
                                yaxis_title='Thickness [nm]')
            return fig

        def CA_CLPos(self):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            try:
                Humidity_data = self.data['HME_cell']
                fig.add_trace(go.Scattergl(x=Humidity_data['time'], y=Humidity_data['Humidity'],
                            mode='markers',
                            name='Humidity cell'),
                            secondary_y=True,
                )
            except:
                pass
            try:
                Humidity_room = self.data['HME_data_room']
                fig.add_trace(go.Scattergl(x=Humidity_room['time'], y=Humidity_room['Humidity'],
                            mode='markers',
                            name='Humidity room'),
                            secondary_y=True,
                )
            except:
                pass
            fig.add_trace(go.Scattergl(x=self.data['Ellipsometry']["time"], y=self.data['Ellipsometry']['Thickness_Brush'],
                        mode='markers',
                        name='Thickness'),
                        secondary_y=False,
            )
            fig.update_layout(xaxis_title='Time')

            fig.update_yaxes(title_text="Thickness [nm]", secondary_y=False)
            fig.update_yaxes(title_text="Humidity [%]", secondary_y=True)

            return fig

        def Flow_Time(self):
            if self.has_sub:
                Humidity_data = self.data['HME_data']
                MFL_H2O_data = self.data['MFL_H2O_data']
                MFL_N2_data = self.data['MFL_N2_data']
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scattergl(x=Humidity_data['time'], y=Humidity_data['Humidity'],
                            mode='markers',
                            name='Humidity'),
                            secondary_y=True,
                )
                fig.add_trace(go.Scattergl(x=MFL_H2O_data['time'], y=MFL_H2O_data['Flow (Std.)'],
                            mode='markers',
                            name='Flow H2O'),
                            secondary_y=False,
                )
                fig.add_trace(go.Scattergl(x=MFL_N2_data['time'], y=MFL_N2_data['Flow (Std.)'],
                            mode='markers',
                            name='Flow N2'),
                            secondary_y=False,
                )
                fig.update_layout(xaxis_title='Time')

                fig.update_yaxes(title_text="Flow rate [Std.]", secondary_y=False)
                fig.update_yaxes(title_text="Humidity [%]", secondary_y=True)

            else:
                print('No data found')


            return fig

        def Humidity_all(self):
            if self.has_sub:
                Humidity_data = self.data['HME_data_room']
                fig = go.Figure()
                for col in Humidity_data.columns:
                    if col == 'time':
                        continue
                    fig.add_trace(go.Scattergl(x=Humidity_data['time'], y=Humidity_data[col],
                                mode='markers',
                                name=col)
                    )
                fig.update_layout(  xaxis_title='Humidity [%]',
                                    yaxis_title='Thickness [nm]')

            else:
                print('No data found')
            return fig

        def Flow_all_N2(self):
            if self.has_sub:
                data = self.data['MFL_N2_data']
                fig = go.Figure()
                for col in data.columns:
                    if col == 'time':
                        continue
                    fig.add_trace(go.Scattergl(x=data['time'], y=data[col],
                                mode='markers',
                                name=col)
                    )
                fig.update_layout(  xaxis_title='Humidity [%]',
                                    yaxis_title='Thickness [nm]')
            else:
                print('No data found')
            return fig
        
        def Flow_all_H2O(self):
            if self.has_sub:
                data = self.data['MFL_H2O_data']
                fig = go.Figure()
                for col in data.columns:
                    if col == 'time':
                        continue
                    fig.add_trace(go.Scattergl(x=data['time'], y=data[col],
                                mode='markers',
                                name=col)
                    )
                fig.update_layout(  xaxis_title='Humidity [%]',
                                    yaxis_title='Thickness [nm]')
            else:
                print('No data found')
            return fig

        def Elli_all(self):
            if self.has_sub:
                data = self.data
                fig = go.Figure()
                for col in data.columns:
                    if col == 'time':
                        continue
                    fig.add_trace(go.Scattergl(x=data['time'], y=data[col],
                                mode='markers',
                                name=col)
                    )
                fig.update_layout(  xaxis_title='Humidity [%]',
                                    yaxis_title='Thickness [nm]')
            else:
                print('No data found')
            return fig
        Flow_all_H2O



    value = 'temp'

    global fig
    app = DjangoDash(name=dash_name, id='target_id')
    cwd = os.getcwd()
    rel_path = get_BasePath()
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
        html.Div([dcc.Dropdown(id='my-dropdown1',
                                                            options=[{'label': 'Time / Thickness', 'value': 'CA/Time'},
                                                                        {'label': 'Select plot', 'value': 'sel_plot'},
                                                                        {'label': 'Humidity / Thickness', 'value': 'CA/CL_Pos'},
                                                                        {'label': 'Humidity / Thickness comp', 'value': 'CA/Run_no'},
                                                                        {'label': 'Humidity / Massflow', 'value': 'Flow/Time'},
                                                                        {'label': 'Humidity all', 'value': 'Humidity_all'},
                                                                        {'label': 'Flow all H2O', 'value': 'Flow_all_H2O'},
                                                                        {'label': 'Flow all N2', 'value': 'Flow_all_N2'},
                                                                        {'label': 'Elli all', 'value': 'Elli_all'},
                                                                    ],
                                                            value='CA/Time',
                                                            className='col-md-12',
                                                            ),
                                                ]),

        html.Div(id='Plot_sel_dropdown', children = [
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y1',
                value=['MTL', 'SF'],
                multi=True,
                style={'width': '33%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y2',
                value=['MTL', 'SF'],
                multi=True,
                style={'width': '33%', 'display': 'table-cell'},
            ),
            html.Button('Plot', id='Btn_Plot'),
        ], style={'width': '100%', 'display': 'flex', 'flex-direction': 'row'},),
        dcc.Input(id='target_id', type='hidden', value='1'),
        html.Div(id='placeholder', style={'display': 'none'}),
        dcc.Graph(
            id='example-graph',
            figure=fig,
        ),
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
            Input('MS_drop_y2', 'value'),]
            )
    def update_sel_list(select_y1, select_y2, *args,**kwargs):
        style={'display': 'none'}
        GenFig.select_y1 = select_y1
        GenFig.select_y2 = select_y2
        return style

    @app.callback(
            [Output(component_id='MS_drop_y1', component_property='style'),
            Output(component_id='MS_drop_y2', component_property='style'),
            Output(component_id='Btn_Plot', component_property='style'),
            Output(component_id='Sel_plot_graph', component_property='style'),
            Output(component_id='example-graph', component_property='style'),],
            [Input('my-dropdown1', 'value')]
            )
    def update_visible(Graph_select, *args,**kwargs):
        if Graph_select != 'sel_plot':
            style={'display': 'none'}
            style_g={'display': 'block'}
            return [style, style, style, style, style_g]
        else:
            style_d={'width': '33%', 'display': 'table-cell'}
            style_b={'display': 'table-cell'}
            style_g={'display': 'block'}
            style={'display': 'none'}
            return [style_d, style_d, style_b, style_g, style]

    @app.callback(
        Output(component_id='example-graph', component_property='figure'),
        [Input('my-dropdown1', 'value')]
    )

    def update_figure(Graph_select, *args,**kwargs):
        global fig
        if Graph_select == 'CA/Time':
            fig = GenFig.CA_Time()
        if Graph_select == 'sel_plot':
            fig = GenFig.sel_plot()
        elif Graph_select == 'CA/BD':
            fig = GenFig.CA_BD()
        elif Graph_select == 'CA/Run_no':
            fig = GenFig.CA_RunNo()
        elif Graph_select == 'CA/CL_Pos':
            fig = GenFig.CA_CLPos()
        elif Graph_select == 'Flow/Time':
            fig = GenFig.Flow_Time()
        elif Graph_select == 'Humidity_all':
            fig = GenFig.Humidity_all()
        elif Graph_select == 'Flow_all_N2':
            fig = GenFig.Flow_all_N2()
        elif Graph_select == 'Flow_all_H2O':
            fig = GenFig.Flow_all_H2O()
        elif Graph_select == 'Elli_all':
            fig = GenFig.Elli_all()

        return fig

    @app.callback(
        [Output(component_id='MS_drop_y1', component_property='options'),
        Output(component_id='MS_drop_y2', component_property='options'),
        Output("loading-output", "children"),],
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),])
    def update_output(n_clicks, target_id, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data_name in GenFig.data:
                for col in GenFig.data[data_name].columns:
                    values = [data_name + '-' + col]*len(label_names)
                    axis_options.append(dict(zip(label_names, values)))
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
        return [axis_options, axis_options, return_str]
