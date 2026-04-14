from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import nd2
import numpy as np
from urllib.parse import parse_qs
import os
import time
import pandas as pd

# IMPORTS
from Lab_Misc.Load_Data import Load_MFP_Path
from Analysis.models import MFPAnalysis
from Analysis.scripts.MFP_Analyze import run_full_analysis
from Analysis.scripts.MFP_Tracking_Logic import process_single_frame

app = DjangoDash('MFP_Tuning')

def load_img_data(nd_file, frame_idx, channel_idx):
    arr = nd_file.asarray()
    dims = {k.lower(): v for k, v in nd_file.sizes.items()}
    try:
        if 'z' in dims:
            if 'c' in dims: return np.max(arr[int(frame_idx), :, int(channel_idx), :, :], axis=0)
            else: return np.max(arr[int(frame_idx), :, :, :], axis=0)
        else:
            if 'c' in dims: return arr[int(frame_idx), int(channel_idx), :, :]
            else: return arr[int(frame_idx), :, :]
    except IndexError: return None

# =========================================================
# LAYOUT
# =========================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='entry-id'), 
    
    html.H4("MFP Parameter Tuner"),
    
    html.Div([
        # ZEILE 1
        html.Div([
            html.Div([
                html.Label("1. Kanal wählen:"),
                dcc.RadioItems(id='channel-select', options=[], value=None, labelStyle={'marginRight': '15px', 'display': 'inline-block', 'fontWeight': 'bold'})
            ], style={'width': '35%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("2. Frame wählen:"),
                dcc.Slider(id='frame-slider', min=0, max=100, step=1, value=0, tooltip={"placement": "bottom", "always_visible": True}),
            ], style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingLeft': '10px'}),
        ], style={'padding': '15px', 'borderBottom': '1px solid #ccc'}),

        # ZEILE 2: PARAMETER
        html.Div([
            html.Div([
                html.Label("Detection Diameter (px):"),
                dcc.Input(id='diameter-input', type='number', value=15, min=3, step=2, style={'width': '100%'}),
                html.Label("Threshold (MinMass):", style={'marginTop': '10px'}),
                dcc.Input(id='threshold-input', type='number', value=10.0, step=0.1, style={'width': '100%'}),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Noise Size (Filter px):", style={'fontWeight': 'bold', 'color': '#007bff'}),
                dcc.Input(id='noise-size-input', type='number', value=3.0, step=0.5, min=0, style={'width': '100%'}),
                html.Label("Min Merge Distance (px):", style={'marginTop': '10px'}),
                dcc.Input(id='mindist-input', type='number', value=70, step=5, style={'width': '100%'}),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("Ansicht:", style={'fontWeight': 'bold'}),
                dcc.Checklist(
                    id='view-options',
                    options=[{'label': ' Show Filtered Image', 'value': 'show_filtered'}, {'label': ' Show Raw Candidates', 'value': 'show_raw'}],
                    value=['show_raw'], style={'marginTop': '10px'}
                )
            ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        ], style={'padding': '15px'}),
        
        # ZEILE 3: Buttons
        html.Div([
            html.Button("Show Gallery", id='gallery-btn', n_clicks=0, className="btn btn-warning"),
            html.Button("Vorschau aktualisieren", id='preview-btn', n_clicks=0, className="btn btn-info", style={'marginLeft': '10px'}),
            html.Button("💾 Save & RUN ANALYSIS", id='run-btn', n_clicks=0, className="btn btn-danger", style={'float': 'right'}),
        ], style={'padding': '10px'}),
        
    ], style={'backgroundColor': '#f0f0f0', 'padding': '5px', 'borderRadius': '5px'}),

    # OUTPUT
    dcc.Loading(children=[dcc.Graph(id='preview-image', style={'height': '750px'})], type="circle"),
    html.Br(),
    # HIER IST DAS STATUS OUTPUT FELD
    dcc.Loading(children=[html.Div(id='status-output', style={'marginTop': '10px', 'fontWeight': 'bold', 'fontSize': '1.2em'})], type="default", color="red")
])

# =========================================================
# CALLBACKS
# =========================================================

@app.callback(
    [Output('frame-slider', 'max'), Output('frame-slider', 'marks'), 
     Output('entry-id', 'data'), 
     Output('diameter-input', 'value'), Output('threshold-input', 'value'),
     Output('mindist-input', 'value'), Output('noise-size-input', 'value'),
     Output('channel-select', 'options'), Output('channel-select', 'value')],
    [Input('url', 'search')], [State('entry-id', 'data')]
)
def init_app(search, current_id, **kwargs):
    entry_id = None
    if search:
        try: entry_id = parse_qs(search.lstrip('?'))['id'][0]
        except: pass
    if not entry_id: entry_id = current_id
    def_ret = (10, {}, entry_id, 15, 10, 70, 3, [], None)
    if not entry_id: return def_ret

    try:
        analysis, created = MFPAnalysis.objects.get_or_create(Entry_id=entry_id)
        dia = getattr(analysis, 'Particle_Diameter', 15)
        thr = getattr(analysis, 'Threshold', 10.0)
        mdist = getattr(analysis, 'Min_Dist', 70) 
        nsize = getattr(analysis, 'Noise_Size', 3.0)
        saved_chan = getattr(analysis, 'Detect_Channel', 0)

        path = Load_MFP_Path(entry_id)
        if not path: return def_ret
        
        with nd2.ND2File(path) as f: 
            max_f = f.shape[0]-1
            sizes = {k.lower(): v for k, v in f.sizes.items()}
            if 'c' in sizes:
                count = sizes['c']
                channel_opts = [{'label': f'Channel {i}', 'value': i} for i in range(count)]
                final_chan = None if (created or saved_chan >= count) else saved_chan
            else:
                channel_opts = [{'label': 'Mono', 'value': 0}]
                final_chan = 0
        
        return max_f, {0: 'Start', max_f: f'End'}, entry_id, dia, thr, mdist, nsize, channel_opts, final_chan
    except: return def_ret

@app.callback(
    Output('preview-image', 'figure'),
    [Input('preview-btn', 'n_clicks'), Input('gallery-btn', 'n_clicks'), 
     Input('entry-id', 'data'), Input('channel-select', 'value')],
    [State('frame-slider', 'value'), 
     State('diameter-input', 'value'), State('threshold-input', 'value'), 
     State('mindist-input', 'value'), State('noise-size-input', 'value'),
     State('view-options', 'value')]
)
def update_graph(btn1, btn2, entry_id, ch, frame, dia, thres, min_dist, noise_size, view_opts):
    if not entry_id: return go.Figure()
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'entry-id'

    try:
        path = Load_MFP_Path(entry_id)
        if not path: return go.Figure(layout=dict(title="Pfad Fehler"))
        show_gallery = (trigger_id == 'gallery-btn') or (ch is None)

        if show_gallery: 
            with nd2.ND2File(path) as f:
                sizes = {k.lower(): v for k, v in f.sizes.items()}
                n_ch = sizes.get('c', 1)
                fig = make_subplots(rows=1, cols=n_ch, subplot_titles=[f"Channel {i}" for i in range(n_ch)])
                for i in range(n_ch):
                    img = load_img_data(f, 0, i)
                    if img is not None:
                        fig.add_trace(go.Heatmap(z=img, colorscale='gray', showscale=False), row=1, col=i+1)
                        fig.update_yaxes(scaleanchor=f"x{i+1}", scaleratio=1, row=1, col=i+1)
                fig.update_layout(height=600, title="Kanal Übersicht")
                return fig
        else:
            if not min_dist: min_dist = 70
            if not noise_size: noise_size = 3.0
            
            with nd2.ND2File(path) as f:
                img = load_img_data(f, frame, ch)
                if img is None: return go.Figure(layout=dict(title="Fehler beim Laden"))
                
                # --- LOGIK AUFRUF ---
                df_raw, df_final, img_filtered = process_single_frame(img, dia, thres, min_dist, noise_size)
                
                display_img = img_filtered if 'show_filtered' in view_opts else img
                fig = px.imshow(display_img, color_continuous_scale='gray', origin='upper')
                
                if 'show_raw' in view_opts and not df_raw.empty:
                    fig.add_trace(go.Scatter(x=df_raw['x'], y=df_raw['y'], mode='markers', marker=dict(color='cyan', symbol='x', size=6), name='Raw', opacity=0.6))

                if not df_final.empty:
                    # TRENNUNG: Valid vs. Fallback
                    # Falls 'valid_fit' fehlt, nehmen wir an, alles ist valide
                    if 'valid_fit' not in df_final.columns: df_final['valid_fit'] = True
                    
                    df_good = df_final[df_final['valid_fit'] == True]
                    df_bad = df_final[df_final['valid_fit'] == False]
                    
                    # 1. Gute Messungen (Rot)
                    if not df_good.empty:
                        # fillna(dia) verhindert Absturz falls real_size leer ist
                        sizes = df_good['real_size'].fillna(dia)
                        fig.add_trace(go.Scatter(
                            x=df_good['x'], y=df_good['y'], mode='markers',
                            marker=dict(
                                color='red', 
                                symbol='circle-open', 
                                size=sizes, 
                                line=dict(width=2)
                            ),
                            name='Measured (Real)'
                        ))
                    
                    # 2. Schlechte Messungen (Orange)
                    if not df_bad.empty:
                        sizes_bad = df_bad['real_size'].fillna(dia)
                        fig.add_trace(go.Scatter(
                            x=df_bad['x'], y=df_bad['y'], mode='markers',
                            marker=dict(
                                color='orange', 
                                symbol='circle-open', 
                                size=sizes_bad, 
                                # WICHTIG: 'dash' entfernt! Wir machen die Linie dünner zur Unterscheidung.
                                line=dict(width=1) 
                            ),
                            name='Fallback (Est.)'
                        ))

                fig.update_layout(title=f"Frame {frame} | Ch {ch} | Detected: {len(df_final)}")
                return fig
    except Exception as e: return go.Figure(layout=dict(title=f"Error: {e}"))

@app.callback(
    Output('status-output', 'children'),
    [Input('run-btn', 'n_clicks')],
    [State('diameter-input', 'value'), State('threshold-input', 'value'), 
     State('mindist-input', 'value'), State('noise-size-input', 'value'),
     State('channel-select', 'value'), State('entry-id', 'data')]
)
def run_analysis_callback(n_clicks, dia, thres, min_dist, nsize, ch, entry_id, **kwargs):
    if n_clicks == 0 or not entry_id: return ""
    
    # STATUS PRINT IM TERMINAL
    print("\n" + "#"*50)
    print(f"### STARTE ANALYSE FÜR ID: {entry_id} ###")
    print("#"*50)
    
    try:
        analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
        if dia % 2 == 0: dia += 1
        
        # Speichern
        analysis.Particle_Diameter = dia
        analysis.Threshold = thres
        if hasattr(analysis, 'Min_Dist'): analysis.Min_Dist = float(min_dist)
        if hasattr(analysis, 'Detect_Channel'): analysis.Detect_Channel = int(ch)
        if hasattr(analysis, 'Noise_Size'): analysis.Noise_Size = float(nsize)
        analysis.save()
        print(" -> Parameter in DB gespeichert.")
        print(" -> Starte 'run_full_analysis'. Bitte Terminal beobachten für Fortschritt...")
        
        # Start
        start_t = time.time()
        success, msg = run_full_analysis(analysis)
        end_t = time.time()
        
        duration = round(end_t - start_t, 2)
        print(f" -> Fertig in {duration}s. Success: {success}")
        
        if success:
            link = f"/Analysis/MFP_Dashboard/{entry_id}" # <--- Link zur zukünftigen Django View (mit Header) statt Direktlink
            return html.Div([
                html.Span(f"✅ Analyse fertig ({duration}s)! ", style={'color':'green'}), 
                html.Br(), 
                html.A("Zum Dashboard", href=link, target="_blank", className="btn btn-success")
            ])
        else: 
            return html.Div(f"Fehler bei Analyse: {msg}", style={'color': 'red'})

    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Systemfehler (siehe Terminal): {str(e)}", style={'color': 'red', 'backgroundColor': '#ffeeee', 'padding': '10px'})