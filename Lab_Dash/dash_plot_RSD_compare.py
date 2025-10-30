import json
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from django_plotly_dash import DjangoDash
from Analysis.RSD import RSD
from Lab_Misc import General
from plotly.subplots import make_subplots

def conv(x):
    return x.replace(',', '.').encode()

def Gen_dash(dash_name):
    class Gen_fig():
        # Define colors for the plots
        colours = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # Load data for a given target ID
        def load_data(self, target_id):
            try:
                self.entry = RSD(target_id)
                self.entry.Merge_LSP_MFR()
                os.chdir(cwd)
                # Reset the index of RSD data
                self.entry.RSD_data.reset_index(drop=True, inplace=True)
                return True, 'Data loaded!'
            except:
                return False, 'No data found!'

        # Create a scatter plot figure
        def create_figure(self, x, y, index, name, selectedpoints=None, drop=None, is_flowrate=False):
            if drop is None:
                i_drop = 0
            else:
                i_drop = drop - 1
            color = self.colours[i_drop % len(self.colours)]
            
            # Define a darker color for flowrate
            if is_flowrate:
                color = self.darken_color(color)
            
            if len(selectedpoints) == 0:
                return go.Scattergl(
                    x=x, y=y, mode='markers', name=name,
                    marker={'color': color, 'size': 5},
                    customdata=index  # Include the original DataFrame index
                )
            if selectedpoints is not None and drop is not None:
                selectedpoints = [i for i in selectedpoints if self.entry.RSD_data.iloc[i]['Drop_Number'] == drop]
                if len(selectedpoints) > 0:
                    drop_loc_data = self.entry.RSD_data[self.entry.RSD_data['Drop_Number'] == drop]
                    selectedpoints = [drop_loc_data.index.get_loc(i) for i in selectedpoints]
            # Convert index to a list of integers
            return go.Scattergl(
                x=x, y=y, mode='markers', name=name, selectedpoints=selectedpoints,
                marker={'color': color, 'size': 5},
                unselected={'marker': {'color': f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2)', 'size': 3}},
                customdata=index  # Include the original DataFrame index
            )

        # Method to darken a color
        def darken_color(self, color, factor=0.7):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f'#{r:02x}{g:02x}{b:02x}'

        # Generate Contact Angle vs Time plot
        def CA_time(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            try:
                if selected_drops:
                    data = self.entry.merged[self.entry.RSD_data['Drop_Number'].isin(selected_drops)]
                else:
                    data = self.entry.merged
                
                for i, drop in enumerate(data['Drop_Number'].unique()):
                    drop_data = data[data['Drop_Number'] == drop]
                    fig.add_trace(
                        self.create_figure(drop_data['time_loc'], drop_data['flowrate'], drop_data.index, f'Flowrate {drop}', selectedpoints, drop, is_flowrate=True),
                        secondary_y=True
                    )
            except:
                print('No LSP found')
            if selected_drops:
                data = self.entry.RSD_data[self.entry.RSD_data['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.RSD_data
            for i, drop in enumerate(data['Drop_Number'].unique()):
                drop_data = data[data['Drop_Number'] == drop]
                if selected_side in ['both', 'left']:
                    fig.add_trace(
                        self.create_figure(drop_data['time_loc'], drop_data['CA_L'], drop_data.index, f'CA left Drop {drop}', selectedpoints, drop),
                        secondary_y=False
                    )
                if selected_side in ['both', 'right']:
                    fig.add_trace(
                        self.create_figure(drop_data['time_loc'], drop_data['CA_R'], drop_data.index, f'CA right Drop {drop}', selectedpoints, drop),
                        secondary_y=False
                    )

            fig.update_layout(
                xaxis_title='Time',
                yaxis_title='Contact angle [°]',
                yaxis2_title='Flowrate'
            )
            return fig
        
                # Function to display only contact angle
        def CA_only(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            if selected_drops:
                data = self.entry.RSD_data[self.entry.RSD_data['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.RSD_data
            for i, drop in enumerate(data['Drop_Number'].unique()):
                drop_data = data[data['Drop_Number'] == drop]
                if selected_side in ['both', 'left']:
                    fig.add_trace(self.create_figure(drop_data['time_loc'], drop_data['CA_L'], drop_data.index, f'CA left Drop {drop}', selectedpoints, drop))
                if selected_side in ['both', 'right']:
                    fig.add_trace(self.create_figure(drop_data['time_loc'], drop_data['CA_R'], drop_data.index, f'CA right Drop {drop}', selectedpoints, drop))

            fig.update_layout(xaxis_title='Time', yaxis_title='Contact angle [°]')
            return fig

        # Function to display only flowrate
        def flowrate_only(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            try:
                if selected_drops:
                    data = self.entry.merged[self.entry.RSD_data['Drop_Number'].isin(selected_drops)]
                else:
                    data = self.entry.merged
                
                for i, drop in enumerate(data['Drop_Number'].unique()):
                    drop_data = data[data['Drop_Number'] == drop]
                    fig.add_trace(self.create_figure(drop_data['time_loc'], drop_data['flowrate'], drop_data.index, f'Flowrate {drop}', selectedpoints, drop))
            except:
                print('No LSP found')

            fig.update_layout(xaxis_title='Time', yaxis_title='Flowrate')
            return fig

        # Generate Contact Angle vs Contact Line Position plot
        def CA_CLPos(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            if selected_drops:
                data = self.entry.merged[self.entry.merged['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.merged
            for i, drop in enumerate(data['Drop_Number'].unique()):
                filtered = data[data['Drop_Number'] == drop]
                label_name = f'Drop {drop} {filtered["gas"].value_counts().idxmax() if "gas" in filtered else ""}'
                if selected_side in ['both', 'left']:
                    fig.add_trace(self.create_figure(filtered['BI_left'], filtered['CA_L'], filtered.index, label_name, selectedpoints, drop))
                if selected_side in ['both', 'right']:
                    fig.add_trace(self.create_figure(filtered['BI_right'], filtered['CA_R'], filtered.index, label_name, selectedpoints, drop))
            fig.update_layout(xaxis_title='Contact line position [mm]', yaxis_title='Contact angle [°]')
            return fig

        # Generate Contact Line Speed plot
        def CL_Speed(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            if selected_drops:
                data = self.entry.merged[self.entry.merged['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.merged
            for i, drop in enumerate(data['Drop_Number'].unique()):
                filtered = data[data['Drop_Number'] == drop]
                label_name = f'Drop {drop} {filtered["gas"].value_counts().idxmax() if "gas" in filtered else ""}'
                if selected_side in ['both', 'left']:
                    fig.add_trace(self.create_figure(filtered['BI_left'], filtered['speed_left_avg'], filtered.index, label_name, selectedpoints, drop))
                if selected_side in ['both', 'right']:
                    fig.add_trace(self.create_figure(filtered['BI_right'], filtered['speed_right_avg'], filtered.index, label_name, selectedpoints, drop))
            fig.update_layout(xaxis_title='Contact line position [mm]', yaxis_title='Contact line speed [m/s]')
            return fig

        # Generate Contact Angle vs Contact Line Speed plot
        def CA_CLSpeed(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            if selected_drops:
                data = self.entry.merged[self.entry.merged['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.merged
            for i, drop in enumerate(data['Drop_Number'].unique()):
                filtered = data[data['Drop_Number'] == drop]
                label_name = f'Drop {drop} {filtered["gas"].value_counts().idxmax() if "gas" in filtered else ""}'
                if selected_side in ['both', 'left']:
                    fig.add_trace(self.create_figure(filtered['speed_left_avg'], filtered['CA_L'], filtered.index, label_name, selectedpoints, drop))
                if selected_side in ['both', 'right']:
                    fig.add_trace(self.create_figure(filtered['speed_right_avg'], filtered['CA_R'], filtered.index, label_name, selectedpoints, drop))
            fig.update_layout(xaxis_title='Contact line speed [m/s]', yaxis_title='Contact angle [°]')
            return fig
        
        def CA_CLSpeed_avg(self, selected_drops=None, selectedpoints=None, selected_side='both'):
            fig = go.Figure()
            if selected_drops:
                data = self.entry.merged[self.entry.merged['Drop_Number'].isin(selected_drops)]
            else:
                data = self.entry.merged

            for i, drop in enumerate(data['Drop_Number'].unique()):
                filtered = data[data['Drop_Number'] == drop]
                label_name = f'Drop {drop} {filtered["gas"].value_counts().idxmax() if "gas" in filtered else ""}'
                
                avg_speed = (filtered['speed_left_avg'] + filtered['speed_right_avg']) / 2
                avg_CA = (filtered['CA_L'] + filtered['CA_R']) / 2
                
                fig.add_trace(self.create_figure(avg_speed, avg_CA, filtered.index, label_name, selectedpoints, drop))

            fig.update_layout(xaxis_title='Average contact line speed [m/s]', yaxis_title='Average contact angle [°]')
            return fig


    app = DjangoDash(name=dash_name)
    cwd = os.getcwd()
    GenFig = Gen_fig()


    # Define the layout of the Dash app
    app.layout = html.Div([
        # Row for dropdowns to select drops and sides
        html.Div([
            dcc.Dropdown(id='drop-selector', options=[], multi=True, style={'flex': 2, 'margin-right': '10px'}),
            html.Div([
                dcc.Dropdown(id='side-selector', options=[
                    {'label': 'Left', 'value': 'left'},
                    {'label': 'Right', 'value': 'right'},
                    {'label': 'Both', 'value': 'both'}
                ], value='both', style={'flex': 1, 'margin-right': '10px'}),
                dcc.Dropdown(id='link-selector', options=[
                    {'label': 'All by "and"', 'value': 'and'},
                    {'label': 'All by "or"', 'value': 'or'},
                    {'label': '2 by "and" and 1 by "or"', 'value': 'mixed'}
                ], value='or', style={'flex': 1})
            ], style={'display': 'flex', 'flex': 1})
        ], style={'display': 'flex', 'margin-bottom': '20px'}),
        # Row for graph type dropdowns
        html.Div([
            dcc.Dropdown(id='dropdown-g1', options=[
                {'label': 'CA time', 'value': 'CA_time'},
                {'label': 'CA / CL_Pos', 'value': 'CA_CLPos'},
                {'label': 'CL_Speed', 'value': 'CL_Speed'},
                {'label': 'CA / CL_Speed', 'value': 'CA_CLSpeed'},
                {'label': 'CA / CL_Speed (avg)', 'value': 'CA_CLSpeed_avg'},
                {'label': 'CA only', 'value': 'CA_only'},
                {'label': 'Flowrate only', 'value': 'flowrate_only'}
            ], value='CA_time', style={'flex': 1, 'margin-right': '10px'}),
            dcc.Dropdown(id='dropdown-g2', options=[
                {'label': 'CA time', 'value': 'CA_time'},
                {'label': 'CA / CL_Pos', 'value': 'CA_CLPos'},
                {'label': 'CL_Speed', 'value': 'CL_Speed'},
                {'label': 'CA / CL_Speed', 'value': 'CA_CLSpeed'},
                {'label': 'CA / CL_Speed (avg)', 'value': 'CA_CLSpeed_avg'},
                {'label': 'CA only', 'value': 'CA_only'},
                {'label': 'Flowrate only', 'value': 'flowrate_only'}
            ], value='CA_CLPos', style={'flex': 1, 'margin-right': '10px'}),
            dcc.Dropdown(id='dropdown-g3', options=[
                {'label': 'CA time', 'value': 'CA_time'},
                {'label': 'CA / CL_Pos', 'value': 'CA_CLPos'},
                {'label': 'CL_Speed', 'value': 'CL_Speed'},
                {'label': 'CA / CL_Speed', 'value': 'CA_CLSpeed'},
                {'label': 'CA / CL_Speed (avg)', 'value': 'CA_CLSpeed_avg'},
                {'label': 'CA only', 'value': 'CA_only'},
                {'label': 'Flowrate only', 'value': 'flowrate_only'}
            ], value='CL_Speed', style={'flex': 1})
        ], style={'display': 'flex', 'margin-bottom': '20px'}),
        # Row for graphs
        html.Div([
            html.Div([
                dcc.Graph(id='g1', config={'displayModeBar': True}, style={'width': '100%', 'height': '680px'})
            ], style={'flex': 1}),
            html.Div([
                dcc.Graph(id='g2', config={'displayModeBar': True}, style={'width': '100%', 'height': '680px'})
            ], style={'flex': 1}),
            html.Div([
                dcc.Graph(id='g3', config={'displayModeBar': True}, style={'width': '100%', 'height': '680px'})
            ], style={'flex': 1})
        ], style={'display': 'flex'}),
        # Hidden input for target ID
        dcc.Input(id='target_id', type='hidden', value='1'),
        # Button to load data
        html.Button('Load data', id='Load_Data'),
        # Loading spinner
        dcc.Loading(id="loading", children=[html.Div([html.Div(id="loading-output")])], type="default")
    ])
    
    # Callback to update the drop selector options based on loaded data
    @app.callback(
        [Output('drop-selector', 'options'),
        Output('drop-selector', 'value')],
        [Input('Load_Data', 'n_clicks')],
        [Input('target_id', 'value')]
    )
    def update_drop_selector(n_clicks, target_id):
        data_was_loaded, _ = GenFig.load_data(target_id)
        if data_was_loaded:
            options = [{'label': f'Drop {drop}', 'value': drop} for drop in GenFig.entry.merged['Drop_Number'].unique()]
            values = [drop['value'] for drop in options]  # Select all drops by default
            return options, values
        return [], []

    # Callback to update the figures based on selected dropdown values and selected data points
    @app.callback(
        [Output('g1', 'figure'),
        Output('g2', 'figure'),
        Output('g3', 'figure')],
        [Input('dropdown-g1', 'value'),
        Input('dropdown-g2', 'value'),
        Input('dropdown-g3', 'value'),
        Input('drop-selector', 'value'),
        Input('side-selector', 'value'),
        Input('link-selector', 'value'),
        Input('g1', 'selectedData'),
        Input('g2', 'selectedData'),
        Input('g3', 'selectedData')]
    )
    def update_figures(Graph_select1, Graph_select2, Graph_select3, selected_drops, selected_side, link_type, selection1, selection2, selection3):
        def get_selected_points(selection):
            if selection and selection['points']:
                return [p['customdata'] for p in selection['points']]  # Use customdata to get the original DataFrame index
            return []

        selectedpoints1 = get_selected_points(selection1)
        selectedpoints2 = get_selected_points(selection2)
        selectedpoints3 = get_selected_points(selection3)

        if link_type == 'and':
            selectedpoints = list(set(selectedpoints1) & set(selectedpoints2) & set(selectedpoints3))
        elif link_type == 'or':
            selectedpoints = list(set(selectedpoints1) | set(selectedpoints2) | set(selectedpoints3))
        elif link_type == 'mixed':
            selectedpoints = list(set(selectedpoints1) & set(selectedpoints2)) + list(set(selectedpoints3))

        fig1 = getattr(GenFig, Graph_select1)(selected_drops, selectedpoints, selected_side)
        fig2 = getattr(GenFig, Graph_select2)(selected_drops, selectedpoints, selected_side)
        fig3 = getattr(GenFig, Graph_select3)(selected_drops, selectedpoints, selected_side)
        return fig1, fig2, fig3

    # Callback to update the loading output message
    @app.callback(Output("loading-output", "children"), [Input('Load_Data', 'n_clicks'), Input('target_id', 'value')])
    def update_output(n_clicks, target_id):
        data_was_loaded, return_str = GenFig.load_data(target_id)
        return return_str + '\n Select the desired plot at the dropdown.' if data_was_loaded else return_str