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
from Lab_Misc import General
from Exp_Main.models import SFG, ExpBase, OCA
from Analysis.models import OszAnalysis, OszBaseParam, OszAnalysisJoin
from Lab_Dash.models import OszAnalysis as OszAnalysis_Dash
from Lab_Dash.models import OszAnalysisEntry
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
                entry = OszAnalysisJoin.objects.get(id = target_id)
                self.entry = entry
                self.Saved_ExpBases = entry.OszAnalysis.all().values_list('id', flat=True)
                return True, 'Data found!'
            except:
                return False, 'No data found!'


        def get_subs(self):
            Sub_Exps = self.entry.Sub_Exp.all()
            return_str = ''
            for Sub_Exp in Sub_Exps:
                Device = Sub_Exp.Device
                model = apps.get_model('Exp_Sub', str(Device.Abbrev))
                Exp_in_Model = model.objects.get(id = Sub_Exp.id)
                if Device.Abbrev == 'MFL':
                    Gas = Exp_in_Model.Gas.first()
                    if Gas.Name == 'H2O':
                        MFL_H2O_data = self.get_sub_csv(Exp_in_Model)
                        #MFL_H2O_data['Flow (Std.)'] = MFL_H2O_data['Flow (Std.)'][MFL_H2O_data['Flow (Std.)']>600]/10#correct for wrong format
                        MFL_H2O_data['Date_Time'] = pd.to_datetime(MFL_H2O_data['Date_Time'], format='%d.%m.%Y %H:%M:%S', errors="coerce")
                        MFL_H2O_data['time'] = MFL_H2O_data['Date_Time'].dt.tz_localize(timezone.get_current_timezone())
                        self.data.update(MFL_H2O_data = MFL_H2O_data)
                        return_str += ', massflow of water stream'
                    if Gas.Name == 'N2':
                        MFL_N2_data = self.get_sub_csv(Exp_in_Model)
                        MFL_N2_data['Date_Time'] = pd.to_datetime(MFL_N2_data['Date_Time'], format='%d.%m.%Y %H:%M:%S', errors="coerce")
                        #MFL_N2_data['Flow (Std.)'] = MFL_N2_data['Flow (Std.)'][MFL_N2_data['Flow (Std.)']>600]/10#correct for wrong format
                        MFL_N2_data['time'] = MFL_N2_data['Date_Time'].dt.tz_localize(timezone.get_current_timezone())
                        self.data.update(MFL_N2_data = MFL_N2_data)
                        return_str += ', massflow of nitrogen stream'
                if Device.Abbrev == 'HME':
                    if Exp_in_Model.Environments == '1':
                        Humidity_data = self.get_sub_dbf(Exp_in_Model)
                        Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
                        Humidity_data['time'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
                        self.data.update(HME_cell = Humidity_data)
                        return_str += ', humidity measurements of the cell'
                        self.has_sub = True
                    if Exp_in_Model.Environments == '2':
                        Humidity_data = self.get_sub_dbf(Exp_in_Model)
                        Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
                        Humidity_data['time'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
                        self.data.update(HME_data_room = Humidity_data)
                        return_str += ', humidity measurements of the room'
                        self.has_sub = True
            return return_str

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

            if isinstance(DashTab.Y_high, float):
                slice_signal = data['Y_axis']<DashTab.Y_high
                data = data[slice_signal]

            if isinstance(DashTab.Y_low, float):
                slice_signal = data['Y_axis']>DashTab.Y_low
                data = data[slice_signal]

            if isinstance(DashTab.X_high, float):
                slice_wavenumber = data['X_axis']<DashTab.X_high
                data = data[slice_wavenumber]

            if isinstance(DashTab.X_low, float):
                slice_wavenumber = data['X_axis']>DashTab.X_low
                data = data[slice_wavenumber]

            return data

        def sel_plot(self):

            fig = go.Figure()
            i = 0
            for y2 in self.select_y2:
                entry = OszAnalysis.objects.get(id = y2)
                Drop_parameters, Osz_fit_parameters, Derived_parameters = Load_Data.Load_OszAnalysis_in_df(y2)
                Positions = ['Right', 'Left', 'Average']
                Param_columns = ['Drop_Nr', 'Max_CL', 'Max_CA', 'Min_CA', 'Min_AdvCA']
                Fit_columns = ['Drop_Nr', 'x_pos', 'y_pos', 'Step_width', 'Step_hight']
                Derived_col = ['Drop_Nr', 'Hit_prec', 'Fit_score']
                plot_columns = ['x_lable', 'y_value', 'y_error', 'Drop_Nr', 'Parameter', 'Position']
                plt_df = pd.DataFrame(columns=plot_columns)
                for selparam in self.Field_Selection:
                    if General.save_index(Param_columns, selparam) != -1:
                        for position in Positions:
                            if General.save_index(self.LoR, position) != -1:
                                plt_dfi = pd.DataFrame(columns=plot_columns)
                                xi = ['Drop_' + str(int(dropNr)) + '_' + str(selparam) + '_' + str(position) for dropNr in Drop_parameters['General']['Drop_Nr']]
                                if position == 'Average':
                                    yi = (Drop_parameters['Right'][selparam] + Drop_parameters['Left'][selparam])/2
                                else:
                                    yi = Drop_parameters[position][selparam]
                                yei = np.zeros(len(xi))
                                plt_dfi['x_lable'] = xi
                                plt_dfi['y_value'] = yi
                                plt_dfi['y_error'] = yei
                                plt_dfi['Drop_Nr'] = [dropNr for dropNr in Drop_parameters['General']['Drop_Nr']]
                                plt_dfi['Parameter'] = selparam
                                plt_dfi['Position'] = position
                                plt_df = plt_df.append(plt_dfi)

                for selparam in self.Field_Selection:
                    if General.save_index(Derived_col, selparam) != -1:
                        for position in Positions:
                            if General.save_index(self.LoR, position) != -1:
                                plt_dfi = pd.DataFrame(columns=plot_columns)
                                xi = ['Drop_' + str(int(dropNr)) + '_' + str(selparam) + '_' + str(position) for dropNr in Derived_parameters['General']['Drop_Nr']]
                                if position == 'Average':
                                    yi = (Derived_parameters['Right'][selparam] + Derived_parameters['Left'][selparam])/2
                                else:
                                    yi = Derived_parameters[position][selparam]
                                yei = np.zeros(len(xi))
                                plt_dfi['x_lable'] = xi
                                plt_dfi['y_value'] = yi
                                plt_dfi['y_error'] = yei
                                plt_dfi['Drop_Nr'] = [dropNr for dropNr in Derived_parameters['General']['Drop_Nr']]
                                plt_dfi['Parameter'] = selparam
                                plt_dfi['Position'] = position
                                plt_df = plt_df.append(plt_dfi)

                    if General.save_index(Fit_columns, selparam) != -1:
                        for position in Positions:
                            if General.save_index(self.LoR, position) != -1:
                                if position == 'Average':
                                    slice_good_fit = (Derived_parameters['Left']['Fit_score'] == 1) & (Derived_parameters['Right']['Fit_score'] == 1)
                                else:
                                    slice_good_fit = np.array(Derived_parameters[position]['Fit_score'].astype(int)) == 1
                                plt_dfi = pd.DataFrame(columns=plot_columns)
                                xi = ['Drop_' + str(int(dropNr)) + '_' + str(selparam) + '_' + str(position) for dropNr in Osz_fit_parameters['General']['General']['Drop_Nr']]
                                if position == 'Average':
                                    yi = (Osz_fit_parameters['Right']['Value'][selparam] + Osz_fit_parameters['Left']['Value'][selparam])/2
                                else:
                                    yi = Osz_fit_parameters[position]['Value'][selparam]

                                if position == 'Average':
                                    yei = (Osz_fit_parameters['Right']['Error'][selparam] + Osz_fit_parameters['Left']['Error'][selparam])/2
                                else:
                                    yei = Osz_fit_parameters[position]['Error'][selparam]
                                yei = np.where(yei > 50, 50, yei).tolist() #limit max error to 50
                                plt_dfi['x_lable'] = np.asarray(xi)[slice_good_fit]
                                plt_dfi['y_value'] = np.asarray(yi)[slice_good_fit]
                                plt_dfi['y_error'] = np.asarray(yei)[slice_good_fit]
                                plt_dfi['Drop_Nr'] = np.asarray([dropNr for dropNr in Osz_fit_parameters['General']['General']['Drop_Nr']])[slice_good_fit]
                                plt_dfi['Parameter'] = selparam
                                plt_dfi['Position'] = position
                                plt_df = plt_df.append(plt_dfi)

                plt_df = plt_df.sort_values(by=['Parameter', 'Position', 'Drop_Nr'])
                fig.add_trace(go.Scattergl(x=plt_df['x_lable'], y=plt_df['y_value'],
                            error_y = dict(
                            type='data', # value of error bar given in data coordinates
                            array=plt_df['y_error'],
                            visible=True,
                            thickness=1.5,),
                            mode='markers',
                            name=entry.Name),
                )

                i+=1
            return fig

    value = 'temp'

    global fig
    global Save_clicked
    Save_clicked = 0
    global Title_clicked
    Title_clicked = 0
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
                                                            options=[{'label': 'Select plot', 'value': 'sel_plot'},
                                                                    ],
                                                            value='sel_plot',
                                                            className='col-md-12',
                                                            ),
                                                ]),

        html.Div(id='title', children = [
            dcc.Textarea(
                id='textarea_tile',
                value='Title',
                style={'width': '50%', 'height': 20},
            ),
            html.Button('Submit', id='textarea_tile_btn'),
        ]),


        html.Div(id='Plot_sel_dropdown', children = [
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y1',
                value=['MTL', 'SF'],
                style={'width': '33%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_y2',
                value=[],
                multi=True,
                style={'width': '33%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_Field_Selection',
                value=[],
                multi=True,
                style={'width': '20%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_LoR',
                value=[],
                multi=True,
                style={'width': '7%', 'display': 'table-cell'},
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
        [Input('Btn_save_image', 'n_clicks'),
        Input('MS_drop_y2', 'value'),
        Input('textarea_tile', 'value'),],
    )
    def save_figure(n_clicks, MS_drop_y2, textarea_tile, *args,**kwargs):
        global Save_clicked
        if n_clicks > Save_clicked:
            Save_clicked = n_clicks
            OszAnalysis_dash_item = OszAnalysis_Dash(Name = textarea_tile)
            OszAnalysis_dash_item.save()
            OszAnalysis_list = OszAnalysis.objects.filter(pk__in=MS_drop_y2)
            OszAnalysis_item = OszAnalysisJoin(Name = textarea_tile, Dash = OszAnalysis_dash_item)
            OszAnalysis_item.save()
            OszAnalysis_item.OszAnalysis.add(*OszAnalysis_list)
            OszAnalysis_item.save()
            for OszAnalysis_id in MS_drop_y2:
                entry = OszAnalysis.objects.get(id = OszAnalysis_id)
                OszAnalysis_entry_item = OszAnalysisEntry(Name = entry.Name, OszAnalysisID = int(OszAnalysis_id))
                OszAnalysis_entry_item.save()
                OszAnalysis_dash_item.Entry.add(OszAnalysis_entry_item)
                OszAnalysis_dash_item.save()

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
        Input('MS_Field_Selection', 'value'),
        Input('MS_LoR', 'value'),]
        )
    def update_sel_list(select_y1, select_y2, Field_Selection, LoR, *args,**kwargs):
        style={'display': 'none'}
        GenFig.select_y1 = select_y1
        GenFig.select_y2 = select_y2
        GenFig.Field_Selection = Field_Selection
        GenFig.LoR = LoR
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
        if Graph_select == 'sel_plot':
            fig = GenFig.sel_plot()
        return fig

    @app.callback(
        [Output(component_id='MS_drop_y1', component_property='options'),
        Output(component_id='MS_Field_Selection', component_property='options'),
        Output(component_id='MS_LoR', component_property='options'),
        Output("loading-output", "children"),
        Output(component_id='MS_drop_y2', component_property='value'),
        Output(component_id='textarea_tile', component_property='value'),],
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),])
    def update_output(n_clicks, target_id, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data in OszAnalysis.objects.all():
                #for col in GenFig.data[data_name].columns:
                values = [data.Name + '-' + 'col', data.id]
                axis_options.append(dict(zip(label_names, values)))
            axis_value = []
            for value in GenFig.Saved_ExpBases:
                entry = OszAnalysis.objects.get(id = value)
                values = [entry.Name, value]
                axis_value.append(value)
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
            axis_value = []
        Field_Selection = [{'label': 'Max_CL', 'value': 'Max_CL'},
                            {'label': 'Max_CA', 'value': 'Max_CA'},
                            {'label': 'Min_CA', 'value': 'Min_CA'},
                            {'label': 'Min_AdvCA', 'value': 'Min_AdvCA'},
                            {'label': 'x_pos', 'value': 'x_pos'},
                            {'label': 'y_pos', 'value': 'y_pos'},
                            {'label': 'Step_width', 'value': 'Step_width'},
                            {'label': 'Step_hight', 'value': 'Step_hight'},
                            {'label': 'Hit_prec', 'value': 'Hit_prec'},
                        ]
        LoR = [
                    {'label': 'Left', 'value': 'Left'},
                    {'label': 'Right', 'value': 'Right'},
                    {'label': 'Average', 'value': 'Average'},
                ]
        return [axis_options, Field_Selection, LoR, return_str, axis_value, GenFig.entry.Dash.Title]

    @app.callback(
            Output(component_id='textarea_tile', component_property='style'),
            [Input('textarea_tile', 'value'),
            Input('textarea_tile_btn', 'n_clicks'),]
            )
    def update_title(title, n_clicks, *args,**kwargs):
        global Title_clicked
        if n_clicks > Title_clicked:
            Title_clicked = n_clicks
            dash = GenFig.entry.Dash
            dash.Title = title
            dash.save()
            style=style={'width': '50%', 'height': 20}
            return style#because a retrun is needed

    @app.callback(
            Output(component_id='MS_drop_y2', component_property='options'),
            [Input('MS_drop_y1', 'value'),
            Input('MS_drop_y2', 'value'),]
            )
    def update_sel_list(select_y1, select_y2, *args,**kwargs):
        sel = OszAnalysis.objects.get(id = select_y1)
        axis_options = []
        label_names = ['label', 'value']
        values = [sel.Name + '-' + 'col', sel.id]
        axis_options.append(dict(zip(label_names, values)))
        """         for value in GenFig.Saved_ExpBases:
            entry = SFG.objects.get(id = value)
            values = [entry.Name, value]
            axis_options.append(dict(zip(label_names, values)))
        #GenFig.Saved_ExpBases = [] """
        for pk in select_y2:
            entry = OszAnalysis.objects.get(id = pk)
            values = [entry.Name, entry.id]
            #values = [entry['label'], entry['value']]
            axis_options.append(dict(zip(label_names, values)))
        return axis_options
