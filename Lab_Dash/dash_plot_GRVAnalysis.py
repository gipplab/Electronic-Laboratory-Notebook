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
from Exp_Main.models import DAF
from Analysis.models import DafAnalysis
from Lab_Misc import Load_Data
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

        def load_data(self, target_id):
            """Load selected analysis entry and corresponding experiments"""
            try:
                try:
                    if self.entry.id == target_id: # update experiments only if analysis in selection box was changed
                        return True, 'Data found!'
                except:
                    pass
                entry = DafAnalysis.objects.get(id = target_id)
                self.entry = entry
                self.select_exp = entry.Experiments.all().values_list('id', flat=True)
                return True, 'Data found!'
            except:
                return False, 'No data found!'

        def sel_plot(self):
            """Plot selected combination of x and y parameters for selected experiments"""
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            plot_columns = ['Name', 'x_value', 'y_value', 'x_error', 'y_error']
            for exp_id in self.select_exp: # plot each experiment seperately to get legend with experiment names
                Drop_parameters, Drop_errors = Load_Data.Load_DAFAnalysis_in_df(exp_id)
                columns = Drop_parameters.columns.values
                for xparam in self.x_Selection:
                    if xparam in columns:
                        for yparam in self.y1_Selection:
                                if yparam in columns:
                                    plt_dfi = pd.DataFrame([[Drop_parameters['Name'][0], Drop_parameters[xparam][0], Drop_parameters[yparam][0], Drop_errors[xparam][0], Drop_errors[yparam][0]]], columns=plot_columns)
                                    fig.add_trace(go.Scatter(x=plt_dfi['x_value'], y=plt_dfi['y_value'],
                                        error_x = dict(type='data', array=plt_dfi['x_error'], visible=True, thickness=1.5,),
                                        error_y = dict(type='data', array=plt_dfi['y_error'], visible=True, thickness=1.5,),
                                        mode='markers', yaxis='y', name=str(plt_dfi['Name'][0])+" ("+str(xparam)+" vs. "+str(yparam)+")"),
                                    )
                        for yparam in self.y2_Selection:
                            if yparam in columns:
                                plt_dfi = pd.DataFrame([[Drop_parameters['Name'][0], Drop_parameters[xparam][0], Drop_parameters[yparam][0], Drop_errors[xparam][0], Drop_errors[yparam][0]]], columns=plot_columns)
                                fig.add_trace(go.Scatter(x=plt_dfi['x_value'], y=plt_dfi['y_value'],
                                    error_x = dict(type='data', array=plt_dfi['x_error'], visible=True, thickness=1.5,),
                                    error_y = dict(type='data', array=plt_dfi['y_error'], visible=True, thickness=1.5,),
                                    mode='markers', yaxis='y2', name=str(plt_dfi['Name'][0])+" ("+str(xparam)+" vs. "+str(yparam)+")"),
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
                id='MS_drop_ana',
                value=GenFig.select_ana,
                style={'width': '33%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_drop_exp',
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
                id='MS_y1_Selection',
                value=[],
                multi=True,
                style={'width': '7%', 'display': 'table-cell'},
            ),
            dcc.Dropdown(
                options=axis_options,
                id='MS_y2_Selection',
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
                    DAFAnalysis_item = DafAnalysis(Name = textarea_tile)
                    DAFAnalysis_item.save()
                except: # change existing analysis entry
                    DAFAnalysis_item = DafAnalysis.objects.get(Name = textarea_tile)
                DAFAnalysis_list = DAF.objects.filter(pk__in=MS_drop_exp)
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
        x_Selection = []
        if data_was_loaded:
            return_str += '.\n Select the desired plot at the dropdown.'
            axis_options = []
            label_names = ['label', 'value']
            for data in DafAnalysis.objects.all(): # options for 1st selection box = all analysis entries
                values = [data.Name + '-' + 'col', data.id]
                axis_options.append(dict(zip(label_names, values)))
            axis_value = []
            columns = []
            for value in GenFig.select_exp: # selected options of 2nd selection box = experiments corresponding to selected analysis entry
                entry = DAF.objects.get(id = value)
                values = [entry.Name, value]
                axis_value.append(value)
                Drop_parameters, Drop_errors = Load_Data.Load_DAFAnalysis_in_df(entry.id)
                columns = columns + list(Drop_parameters.columns.values)
            if len(GenFig.select_exp) > 0:
                columns = list(set(columns)) # remove duplicates from column list
                columns.sort() # sort column options alphabetically
                for param in columns: # options for 3rd selection box (x-axis parameter) = all available columns from analysis result files
                    x_Selection.append({'label': param, 'value': param})
        else:
            axis_options = [
                    {'label': 'Dummy', 'value': 'Dummy'},
                ]
            axis_value = []
        y1_Selection = x_Selection # same options for 4th selection box (y1-axis parameter) as for 3rd
        y2_Selection = x_Selection # same options for 5th selection box (y2-axis parameter) as for 3rd
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
        for entry in DAF.objects.filter(~Q(Link_Result = None)): # selection of all experiments with existing analysis result possible
            values = [entry.Name, entry.id] # experiment options that can be selected in 2nd selection box
            axis_options.append(dict(zip(label_names, values)))
        return [axis_options, select_ana]
