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
from Exp_Main.models import SFG, ExpBase, DAF
from Analysis.models import DafAnalysis
from Lab_Dash.models import DAF as DAF_Dash
from Lab_Dash.models import DafAnalysisEntry
from Exp_Sub.models import LSP
from plotly.subplots import make_subplots
from Lab_Misc import Load_Data

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name, pk):
    class Gen_fig():
        select_y1 = ['']
        select_y2 = ['']
        def load_data(self, target_id):
            try:
                entry = DafAnalysis.objects.get(id = target_id)
                self.entry = entry
                self.Saved_ExpBases = entry.Experiments.all().values_list('id', flat=True)
                return True, 'Data found!'
            except:
                return False, 'No data found!'

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
            for xparam in self.x_Selection:
                for yparam in self.y_Selection:
                    plot_columns = ['x_value', 'y_value', 'x_error', 'y_error']
                    plt_df = pd.DataFrame(columns=plot_columns)
                    for y2 in self.select_y2:
                        # entry = DAF.objects.get(id = y2)
                        Drop_parameters, Drop_errors = Load_Data.Load_DAFAnalysis_in_df(y2)
                        columns = Drop_parameters.columns.values
                        if xparam in columns:
                            if yparam in columns:
                                plt_dfi = pd.DataFrame([[Drop_parameters[xparam][0], Drop_parameters[yparam][0], Drop_errors[xparam][0], Drop_errors[yparam][0]]], columns=plot_columns)
                                plt_df = pd.concat([plt_df, plt_dfi], ignore_index=True)
                    plt_df = plt_df.sort_values(by=['x_value'])
                    fig.add_trace(go.Scattergl(x=plt_df['x_value'], y=plt_df['y_value'],
                                error_x = dict(type='data', array=plt_df['x_error'], visible=True, thickness=1.5,),
                                error_y = dict(type='data', array=plt_df['y_error'], visible=True, thickness=1.5,),
                                mode='markers', name=str(xparam)+" vs. "+str(yparam)),
                    )

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
                id='MS_x_Selection',
                value=[],
                multi=True,
                style={'width': '20%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_y_Selection',
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
            DAF_dash_item = DAF_Dash(Name = textarea_tile)
            DAF_dash_item.save()
            # DAFAnalysis_list = DafAnalysis.objects.filter(pk__in=MS_drop_y2)
            # DAFAnalysis_item = DafAnalysisJoin(Name = textarea_tile, Dash = DAF_dash_item)
            # DAFAnalysis_item.save()
            # DAFAnalysis_item.DAFAnalysis.add(*DAFAnalysis_list)
            # DAFAnalysis_item.save()
            for DafAnalysis_id in MS_drop_y2:
                entry = DafAnalysis.objects.get(id = DafAnalysis_id)
                DAFAnalysis_entry_item = DafAnalysisEntry(Name = entry.Name, DafAnalysisID = int(DafAnalysis_id))
                DAFAnalysis_entry_item.save()
                DAF_dash_item.Entry.add(DAFAnalysis_entry_item)
                DAF_dash_item.save()

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
        Input('MS_x_Selection', 'value'),
        Input('MS_y_Selection', 'value'),]
        )
    def update_sel_list(select_y1, select_y2, x_Selection, y_Selection, *args,**kwargs):
        style={'display': 'none'}
        GenFig.select_y1 = select_y1
        GenFig.select_y2 = select_y2
        GenFig.x_Selection = x_Selection
        GenFig.y_Selection = y_Selection
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
        Output(component_id='MS_x_Selection', component_property='options'),
        Output(component_id='MS_y_Selection', component_property='options'),
        Output("loading-output", "children"),
        Output(component_id='MS_drop_y2', component_property='value'),
        Output(component_id='textarea_tile', component_property='value'),],
        [Input('Load_Data', 'n_clicks'),
        Input('target_id', 'value'),])
    def update_output(n_clicks, target_id, *args,**kwargs):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        x_Selection = []
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data in DafAnalysis.objects.all():
                #for col in GenFig.data[data_name].columns:
                values = [data.Name + '-' + 'col', data.id]
                axis_options.append(dict(zip(label_names, values)))
            axis_value = []
            for value in GenFig.Saved_ExpBases:
                entry = DAF.objects.get(id = value)
                values = [entry.Name, value]
                axis_value.append(value)
            if len(GenFig.Saved_ExpBases) > 0:
                id =  GenFig.Saved_ExpBases[0]
                Drop_parameters, Drop_errors = Load_Data.Load_DAFAnalysis_in_df(id)
                columns = Drop_parameters.columns.values
                for param in columns:
                    x_Selection.append({'label': param, 'value': param})
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
            axis_value = []
        y_Selection = x_Selection
        return [axis_options, x_Selection, y_Selection, return_str, axis_value, GenFig.entry.id]

    @app.callback(
            Output(component_id='textarea_tile', component_property='style'),
            [Input('textarea_tile', 'value'),
            Input('textarea_tile_btn', 'n_clicks'),]
            )
    # def update_title(title, n_clicks, *args,**kwargs):
    #     global Title_clicked
    #     if n_clicks > Title_clicked:
    #         Title_clicked = n_clicks
    #         dash = GenFig.entry.Dash
    #         dash.Title = title
    #         dash.save()
    #         style=style={'width': '50%', 'height': 20}
    #         return style#because a retrun is needed

    @app.callback(
            Output(component_id='MS_drop_y2', component_property='options'),
            [Input('MS_drop_y1', 'value'),
            Input('MS_drop_y2', 'value'),]
            )
    def update_sel_list(select_y1, select_y2, *args,**kwargs):
        sel = DafAnalysis.objects.get(id = select_y1)
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
            entry = DAF.objects.get(id = pk)
            values = [entry.Name, entry.id]
            #values = [entry['label'], entry['value']]
            axis_options.append(dict(zip(label_names, values)))
        return axis_options
