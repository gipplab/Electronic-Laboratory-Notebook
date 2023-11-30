import glob, os
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from django_plotly_dash import DjangoDash
from django.apps import apps
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from Lab_Misc.General import *
import pandas as pd
import numpy as np
from Exp_Main.models import GRV
from Analysis.models import GrvAnalysisJoin, GrvAnalysis, PointsShift
from Lab_Misc import Load_Data
from Lab_Misc.models import SampleGroovedPlate
from django.db.models import Q

def conv(x):
    return x.replace(',', '.').encode()
def Gen_dash(dash_name, pk):
    class Gen_fig():
        select_ana = pk # selected analysis entry (1st selection box)
        select_exp = [] # selected experiments to be plotted (2nd selection box)
        x_Selection = [] # selected parameters to be plotted on x-axis (3rd selection box)
        y1_Selection = [] # selected parameters to be plotted on 1st y-axis (4th selection box)
        y2_Selection = [] # selected parameters to be plotted on 2nd y-axis (5th selection box)
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',]

        def load_data(self, target_id):
            """Load selected analysis entry and corresponding experiments"""
            try:
                try:
                    if self.entry.id == target_id: # update experiments only if analysis in selection box was changed
                        return True, 'Data found!'
                except:
                    pass
                entry = GrvAnalysisJoin.objects.get(id = target_id)
                self.entry = entry
                self.select_exp = entry.GrvAnalysis.all().values_list('id', flat=True)
                return True, 'Data found!'
            except:
                return False, 'No data found!'

        def sel_plot(self):
            """Plot selected combination of x and y parameters for selected experiments"""
            i = 0
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            if self.x_Selection[0] == 'Speed':
                for y2_sel in self.y2_Selection:
                    if y2_sel == 'Diff_steady_static':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                diff_ss = steady_val-static_val
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[speed], y=[diff_ss],
                                    marker=dict(color=self.colours[i]), yaxis='y1', name= entry_full.Name+' ' + line_state),
                                )
                    elif y2_sel == 'steady':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[speed], y=[steady_val],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state),
                                )
                    elif y2_sel == 'static':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[speed], y=[static_val],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state),
                                )
                    elif y2_sel == 'theta':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                theta = np.arcsin(1-steady_val**2/(2*1.48**2))/np.pi*180
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                ca = 10*speed/10/20
                                theta = theta**3
                                fig.add_trace(go.Scatter(x=[ca], y=[theta],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state,),
                                )
                        #fig.update_xaxes(type="log")
                        #fig.update_yaxes(type="log")
                    
                    elif y2_sel == 'virt_theta':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                diff_virt = static_val - np.sqrt(2)*1.48
                                steady_val = steady_val-diff_virt
                                theta = np.arcsin(1-steady_val**2/(2*1.48**2))/np.pi*180
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                ca = 10*speed/10/20
                                
                                #theta = theta**3
                                fig.add_trace(go.Scatter(x=[ca], y=[theta],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state,),
                                )
                        fig.update_xaxes(type="log")
            elif self.x_Selection[0] == 'Groove':
                for y2_sel in self.y2_Selection:
                    if y2_sel == 'Diff_steady_static':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                diff_ss = steady_val-static_val
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[speed], y=[diff_ss],
                                    marker=dict(color=self.colours[i]), yaxis='y1', name= entry_full.Name+' ' + line_state),
                                )
                    elif y2_sel == 'steady':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                #i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                sample = SampleGroovedPlate.objects.get(id = entry_full.Sample_name.id)
                                groove_width = sample.Groove_width_mm
                                i+=int((sample.Ridge_width_mm*10) % 15)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[groove_width], y=[steady_val],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state+' ' + str(speed)),
                                )
                    elif y2_sel == 'static':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                fig.add_trace(go.Scatter(x=[speed], y=[static_val],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state),
                                )
                    elif y2_sel == 'theta':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                theta = np.arcsin(1-steady_val**2/(2*1.48**2))/np.pi*180
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                ca = 10*speed/10/20
                                theta = theta**3
                                fig.add_trace(go.Scatter(x=[ca], y=[theta],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state,),
                                )
                        #fig.update_xaxes(type="log")
                        #fig.update_yaxes(type="log")
                    
                    elif y2_sel == 'virt_theta':
                        for ana_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                            for line_state in self.y1_Selection:
                                i = [i for i, s in enumerate(self.y1_Selection) if line_state in s][0]
                                entry_grv_ana = GrvAnalysis.objects.get(id = ana_id)
                                i+=entry_grv_ana.Exp.Sample_name.id % 15
                                entry_steady = entry_grv_ana.SteadyShift.filter(Type_state = 'steady').first()
                                steady_val = entry_steady.PointsShift.filter(Type_pos = line_state).first().Position
                                
                                entry_static = entry_grv_ana.SteadyShift.filter(Type_state = 'static').first()
                                static_val = entry_static.PointsShift.filter(Type_pos = line_state).first().Position
                                diff_virt = static_val - np.sqrt(2)*1.48
                                steady_val = steady_val-diff_virt
                                theta = np.arcsin(1-steady_val**2/(2*1.48**2))/np.pi*180
                                exp_id = entry_grv_ana.Exp.id
                                entry_full = get_in_full_model(exp_id)
                                speed = entry_full.Plate_speed_mm_s
                                ca = 10*speed/10/20
                                
                                #theta = theta**3
                                fig.add_trace(go.Scatter(x=[ca], y=[theta],
                                    marker=dict(color=self.colours[i]), yaxis='y2', name= entry_full.Name+' ' + line_state,),
                                )
                        fig.update_xaxes(type="log")
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
                id='MS_drop_ana',
                value=GenFig.select_ana,
                style={'width': '30%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_exp',
                value=[],
                multi=True,
                style={'width': '10%', 'display': 'table-cell'},
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
                id='MS_y1_Selection',
                value=[],
                multi=True,
                style={'width': '20%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_y2_Selection',
                value=[],
                multi=True,
                style={'width': '20%', 'display': 'table-cell'},
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
        #html.Button('Save plot', id='Btn_save_plot'),
        #html.Div(id='Save_plot_output'),
    ])

    # @app.callback(
    #     Output(component_id='Save_plot_output', component_property='children'),
    #     [Input('Btn_save_plot', 'n_clicks'),],
    # )
    # def save_fig(n_clicks, *args,**kwargs):
    #     global fig
    #     fig.write_image('fig1.png', width=800, height=400, scale=10, engine='orca')
    #     try:
    #         entry = DAF.objects.get(id = GenFig.select_exp[0])
    #         rel_path = os.path.dirname(os.path.dirname(os.path.dirname(entry.Link)))
    #         path = os.path.join(get_BasePath(), rel_path)
    #         name = str(datetime.datetime.now().strftime('%Y%m%d')) + '_' + str(datetime.datetime.now().strftime('%H%M%S')) + '_DAFI_plot.png'
    #         fig.write_image(os.path.join(path, name), width=800, height=400, scale=10)
    #         return 'Image Saved!'
    #     except:
    #         return 'Nothing saved!'

    @app.callback(
        Output(component_id='Save_output', component_property='children'),
        [Input('Btn_save_image', 'n_clicks'),
        Input('MS_drop_exp', 'value'),
        Input('textarea_tile', 'value'),],
    )
    def save_figure(n_clicks, MS_drop_exp, textarea_tile, *args,**kwargs):
        """Save selected list of experiments to new analysis entry"""
        global Save_clicked
        try:
            if n_clicks > Save_clicked:
                Save_clicked = n_clicks
                try: # create new analysis entry if name does not exist
                    DAFAnalysis_item = GrvAnalysis(Name = textarea_tile)
                    DAFAnalysis_item.save()
                except: # change existing analysis entry
                    DAFAnalysis_item = GrvAnalysis.objects.get(Name = textarea_tile)
                DAFAnalysis_list = GRV.objects.filter(pk__in=MS_drop_exp)
                DAFAnalysis_item.Experiments.set(DAFAnalysis_list)
                return 'Image Saved!'
        except:
            return 'Nothing saved!'

    @app.callback(
        Output(component_id='Sel_plot_graph', component_property='figure'),
        [Input('Btn_Plot', 'n_clicks')],
    )
    def update_figure_Sel_plot(n_clicks, *args,**kwargs):
        fig = GenFig.sel_plot()

        return fig

    @app.callback(
        Output(component_id='placeholder', component_property='style'),
        [Input('MS_drop_ana', 'value'),
        Input('MS_drop_exp', 'value'),
        Input('MS_x_Selection', 'value'),
        Input('MS_y1_Selection', 'value'),
        Input('MS_y2_Selection', 'value'),]
        )
    def update_sel_list(select_ana, select_exp, x_Selection, y1_Selection, y2_Selection, *args,**kwargs):
        style={'display': 'none'}
        GenFig.select_ana = select_ana
        GenFig.select_exp = select_exp
        GenFig.x_Selection = x_Selection
        GenFig.y1_Selection = y1_Selection
        GenFig.y2_Selection = y2_Selection
        return style

    @app.callback(
        [Output(component_id='MS_drop_ana', component_property='style'),
        Output(component_id='MS_drop_exp', component_property='style'),
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
        [Output(component_id='MS_drop_ana', component_property='options'),
        Output(component_id='MS_x_Selection', component_property='options'),
        Output(component_id='MS_y1_Selection', component_property='options'),
        Output(component_id='MS_y2_Selection', component_property='options'),
        Output("loading-output", "children"),
        Output(component_id='MS_drop_exp', component_property='value'),
        Output(component_id='textarea_tile', component_property='value'),],
        [Input('target_id', 'value'),])
    def update_output(target_id, *args,**kwargs):
        """Update options for selection boxes"""
        data_was_loaded, return_str = GenFig.load_data(target_id)
        y1_Selection = []
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data in GrvAnalysis.objects.all(): # options for 1st selection box = all analysis entries
                values = [data.Name + '-' + 'col', data.id]
                axis_options.append(dict(zip(label_names, values)))
            axis_value = []
            for value in GenFig.select_exp: # selected options of 2nd selection box = experiments corresponding to selected analysis entry
                entry = GrvAnalysis.objects.get(id = value)
                values = [entry.Name, value]
                axis_value.append(value)
            for item in PointsShift.Pos_ch: # options for 3rd selection box (x-axis parameter) = all available columns from analysis result files
                y1_Selection.append({'label': item[0], 'value': item[0]})
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
            axis_value = []
        x_Selection = [
                    {'label': 'Speed', 'value': 'Speed'},
                    {'label': 'Groove', 'value': 'Groove'},
                ]
        y2_Selection = [
                    {'label': 'Diff steady static', 'value': 'Diff_steady_static'},
                    
                    {'label': 'virtual bulk', 'value': 'virt_theta'},
                    {'label': 'theta', 'value': 'theta'},
                    {'label': 'steady', 'value': 'steady'},
                    {'label': 'static', 'value': 'static'},
                ]
        return [axis_options, x_Selection, y1_Selection, y2_Selection, return_str, axis_value, GenFig.entry.Name]

    @app.callback(
            Output(component_id='textarea_tile', component_property='style'),
            [Input('textarea_tile', 'value'),
            Input('textarea_tile_btn', 'n_clicks'),]
            )
    def update_title(title, n_clicks, *args,**kwargs):
        """Rename analysis entry to name from title text box"""
        global Title_clicked
        try:
            if n_clicks > Title_clicked:
                Title_clicked = n_clicks
                GenFig.entry.Name = title
                GenFig.entry.save()
                style=style={'width': '50%', 'height': 20}
                return style#because a retrun is needed
        except:
            pass

    @app.callback(
            [Output(component_id='MS_drop_exp', component_property='options'),
            Output(component_id='target_id', component_property='value'),],
            [Input('MS_drop_ana', 'value'),]
            )
    def update_sel_list(select_ana, *args,**kwargs):
        """Update options that can be selected in 2nd selection box"""
        axis_options = []
        label_names = ['label', 'value']
        for entry in GrvAnalysis.objects.all(): # selection of all experiments with existing analysis result possible
            values = [entry.Name, entry.id] # experiment options that can be selected in 2nd selection box
            axis_options.append(dict(zip(label_names, values)))
        return [axis_options, select_ana]
