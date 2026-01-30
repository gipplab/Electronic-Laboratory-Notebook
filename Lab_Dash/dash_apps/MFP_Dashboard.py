from django_plotly_dash import DjangoDash
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import pickle
import os
import json
import traceback
from urllib.parse import parse_qs, unquote

from Lab_Misc.Load_Data import Load_MFP 
from Lab_Misc.General import get_BasePath

from Analysis.models import MFPAnalysis

app = DjangoDash('MFP_Dashboard')

# =========================================================
# LAYOUT
# =========================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='entry-id'),
    
    # WICHTIG: Der "Kickstarter" bleibt drin, weil er funktioniert!
    dcc.Interval(id='kickstarter', interval=500, max_intervals=1),

    html.H2("MFP Analysis Dashboard", style={'textAlign': 'center', 'fontFamily': 'sans-serif'}),
    
    # Kleiner Status-Bereich statt blauer Box
    html.Div([
        html.Button("🔄 Reload", id='reload-btn', n_clicks=0, className="btn btn-sm btn-outline-primary"),
        html.Span(id='loading-status', style={'marginLeft': '15px', 'fontWeight': 'bold', 'color': '#333'})
    ], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #ddd'}),

    dcc.Tabs(id='tabs', value='tab-single', children=[
        dcc.Tab(label='🔎 Single Inspection', value='tab-single', children=[
            html.Div([
                # LINKS
                html.Div([
                    html.Div([
                        html.Label("Channel:", style={'fontWeight': 'bold'}),
                        dcc.RadioItems(id='channel-selector', options=[{'label': 'Detection', 'value': 'detect'}, {'label': 'Measure', 'value': 'measure'}], value='detect', labelStyle={'display': 'inline-block', 'marginRight': '10px'}),
                        dcc.Checklist(id='show-markers-toggle', options=[{'label': ' Markers', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '10px'}),
                    ], style={'marginBottom': '5px'}),
                    
                    dcc.Graph(id='image-plot', style={'height': '65vh'}),
                    
                    # Slider (Marks={} verhindert JS Fehler)
                    dcc.Slider(id='frame-slider', min=0, max=100, value=0, step=1, marks={0:'0'}, tooltip={"placement": "bottom", "always_visible": True})
                ], style={'width': '55%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
                
                # RECHTS
                html.Div([
                    html.Label("Particle ID:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='particle-dropdown', options=[], value=None, clearable=False),
                    dcc.Graph(id='single-intensity-graph', style={'height': '50vh'}),
                    html.Div(id='debug-info', style={'color': 'gray', 'fontSize': '0.8em', 'marginTop': '5px'})
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
            ])
        ]),

        dcc.Tab(label='📊 Global Statistics', value='tab-global', children=[
            html.Div([
                dcc.Dropdown(id='global-id-filter', options=[], multi=True, placeholder="Filter specific IDs..."),
                dcc.Graph(id='global-spaghetti', style={'height': '40vh'}),
                dcc.Graph(id='global-heatmap', style={'height': '50vh'}),
            ], style={'padding': '20px'})
        ])
    ])
])

# =========================================================
# DATA LOADING
# =========================================================
DATA_CACHE = {} 

def get_data(entry_id):
    if not entry_id: return None
    try: entry_id = int(entry_id)
    except: pass
    
    if entry_id in DATA_CACHE: return DATA_CACHE[entry_id]

    try:
        # 1. TABELLE LADEN (via dein Load_Data Skript)
        tracks = Load_MFP(entry_id)
        
        if tracks.empty: 
            print(f"Load_MFP returned empty for {entry_id}")
            return None

        # Index Fix für Dash
        tracks = tracks.reset_index(drop=True)

        # 2. VIDEO LADEN
        # Wir holen den Pfad aus den Tracks (Load_MFP speichert 'Source_File')
        # oder Fallback über das Model
        source_file = None
        
        if 'Source_File' in tracks.columns:
            rel_link = tracks.iloc[0]['Source_File']
            source_file = os.path.join(get_BasePath(), rel_link)
        else:
            # Fallback falls Source_File fehlt
            try: 
                analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
            except: 
                analysis = MFPAnalysis.objects.get(pk=entry_id)
            source_file = os.path.join(get_BasePath(), analysis.Entry.Link)

        vid_detect = None
        vid_measure = None

        if source_file and os.path.exists(source_file):
            import nd2
            # Kanal-Infos brauchen wir trotzdem aus dem Analysis Model
            try:
                analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
            except:
                analysis = MFPAnalysis.objects.get(pk=entry_id)
                
            detect_ch = getattr(analysis, 'Detect_Channel', 0)
            measure_ch = 1 if detect_ch == 2 else 0 
            
            with nd2.ND2File(source_file) as f:
                arr = f.asarray()
                if arr.ndim == 5: 
                    vid_detect = np.max(arr[:, :, detect_ch, :, :], axis=1)
                    vid_measure = np.max(arr[:, :, measure_ch, :, :], axis=1)
                elif arr.ndim == 4:
                    vid_detect = arr[:, detect_ch, :, :]
                    vid_measure = arr[:, measure_ch, :, :]
                else:
                    vid_detect = arr
                    vid_measure = arr
        else:
            print(f"Video file missing: {source_file}")
        
        # Alles zusammenpacken
        data = {
            'tracks': tracks,
            'vid_detect': vid_detect,
            'vid_measure': vid_measure
        }
        
        DATA_CACHE[entry_id] = data
        return data

    except Exception as e:
        print(f"Error in get_data: {e}")
        traceback.print_exc()
        return None

# =========================================================
# CALLBACKS
# =========================================================

# 1. INIT (Exakt die Logik vom Debug-Code, nur andere Outputs)
@app.callback(
    [Output('entry-id', 'data'), Output('loading-status', 'children'),
     Output('particle-dropdown', 'options'), Output('particle-dropdown', 'value'),
     Output('global-id-filter', 'options'),
     Output('frame-slider', 'max'), Output('frame-slider', 'marks')],
    [Input('url', 'search'), Input('kickstarter', 'n_intervals'), Input('reload-btn', 'n_clicks')]
)
def init_dashboard(search, n, clicks):
    entry_id = None
    
    # URL Parsing (Das hat funktioniert!)
    if search:
        try:
            decoded = unquote(search)
            qs = parse_qs(decoded.lstrip('?'))
            if 'id' in qs: 
                entry_id = qs['id'][0]
            elif 'session_state' in qs:
                state = json.loads(qs['session_state'][0])
                entry_id = state.get('MFP_id') or state.get('id')
        except: pass

    # Wenn keine ID da ist -> Fehler anzeigen
    if not entry_id:
        return None, "❌ Keine ID gefunden.", [], None, [], 100, {0:'0'}

    data = get_data(entry_id)
    if not data:
        return entry_id, f"❌ Keine Daten für ID {entry_id} (Bitte 'RUN ANALYSIS' wiederholen).", [], None, [], 100, {0:'0'}
    
    tracks = data['tracks']
    if tracks.empty: return entry_id, "⚠️ 0 Partikel gefunden.", [], None, [], 100, {0:'0'}

    all_particles = sorted(tracks['particle'].unique())
    options = [{'label': f"ID {p}", 'value': p} for p in all_particles]
    first_val = all_particles[0] if all_particles else None
    
    mf = int(tracks['frame'].max())
    marks = {0: 'Start', mf: 'Ende'}
    
    return entry_id, f"✅ ID {entry_id} geladen ({len(all_particles)} Partikel).", options, first_val, options, mf, marks


# 2. VIEW UPDATE (MIT SHAPES FÜR KORREKTEN RADIUS)
@app.callback(
    [Output('image-plot', 'figure'), Output('single-intensity-graph', 'figure'), Output('debug-info', 'children')],
    [Input('frame-slider', 'value'), Input('channel-selector', 'value'), 
     Input('particle-dropdown', 'value'), Input('show-markers-toggle', 'value')],
    [State('entry-id', 'data')]
)
def update_view(frame, channel, pid, markers, entry_id):
    if not entry_id: return go.Figure(), go.Figure(), ""
    data = get_data(entry_id)
    if not data: return go.Figure(), go.Figure(), ""
    
    # Video Check
    if data['vid_detect'] is None: 
        return go.Figure(layout={'title': "Video not found"}), go.Figure(), "Video Missing"

    vid = data['vid_measure'] if channel == 'measure' else data['vid_detect']
    tracks = data['tracks']
    
    if frame >= len(vid): frame = len(vid)-1
    
    # --- 1. BILD (HEATMAP) ---
    fig_img = go.Figure()
    fig_img.add_trace(go.Heatmap(z=vid[frame], colorscale='gray' if channel=='detect' else 'inferno', showscale=False, hoverinfo='skip'))
    
    # --- 2. KREISE (SHAPES) ---
    try:
        shapes = []
        if 'show' in markers:
            df = tracks[tracks['frame'] == frame]
            if not df.empty:
                for _, row in df.iterrows():
                    # RADIUS HOLEN
                    # Wir nutzen 'real_size' direkt als Radius.
                    # (Falls du den Durchmesser meinst, nimm * 0.5 oder * 1.0 je nach Definition in deiner Analyse)
                    r_px = row.get('real_size', 5.0) 
                    if pd.isna(r_px): r_px = 5.0
                    
                    # Ist dieser Punkt ausgewählt?
                    is_sel = (pid is not None) and (int(row['particle']) == int(pid))
                    is_valid = row.get('valid_fit', True)
                    
                    # Stil definieren
                    col = '#00FFFF' if is_sel else ('red' if is_valid else 'orange')
                    lw = 3 if is_sel else 1.5
                    style = 'solid' if is_valid else 'dot'

                    # Shape definieren (X0, Y0 = Oben Links | X1, Y1 = Unten Rechts)
                    shapes.append(dict(
                        type="circle",
                        xref="x", yref="y",
                        x0 = row['x'] - r_px,
                        y0 = row['y'] - r_px,
                        x1 = row['x'] + r_px,
                        y1 = row['y'] + r_px,
                        line = dict(color=col, width=lw, dash=style)
                    ))
        
        # Shapes dem Layout hinzufügen
        fig_img.update_layout(shapes=shapes)

    except Exception as e:
        print(f"Shape Error: {e}")

    # Layout fixieren (Damit Zoom funktioniert & Koordinaten stimmen)
    fig_img.update_layout(
        margin=dict(l=0,r=0,t=30,b=0), height=600, title=f"Frame {frame}",
        xaxis=dict(visible=False, scaleanchor="y"), # Quadratische Pixel
        yaxis=dict(visible=False, autorange='reversed'), # (0,0) ist oben links
        clickmode='event+select'
    )
    
    # --- 3. GRAPH ---
    fig_graph = go.Figure()
    txt = "Select a particle..."
    
    if pid is not None:
        try: pid=int(pid)
        except: pass
        
        t_data = tracks[tracks['particle'] == pid].sort_values('frame')
        fig_graph.add_trace(go.Scatter(x=t_data['frame'], y=t_data['intensity_measure'].fillna(0), mode='lines+markers', name=f"ID {pid}"))
        
        curr = t_data[t_data['frame'] == frame]
        if not curr.empty:
             val = curr['intensity_measure'].fillna(0).values[0]
             r_val = curr['real_size'].values[0] if 'real_size' in curr else 0
             txt = f"ID {pid} | Int: {val:.1f} | Radius: {r_val:.2f}px"
             fig_graph.add_trace(go.Scatter(x=curr['frame'], y=[val], mode='markers', marker=dict(color='red', size=12), name="Current"))
    
    fig_graph.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=40, b=20), title=txt)
    
    return fig_img, fig_graph, txt
    

# 3. GLOBAL STATS
@app.callback(
    [Output('global-spaghetti', 'figure'), Output('global-heatmap', 'figure')],
    [Input('global-id-filter', 'value'), Input('tabs', 'value')],
    [State('entry-id', 'data')]
)
def update_glob(sel, tab, eid):
    if tab != 'tab-global' or not eid: return dash.no_update, dash.no_update
    data = get_data(eid)
    if not data: return go.Figure(), go.Figure()
    tracks = data['tracks']
    df = tracks[tracks['particle'].isin(sel)] if sel else tracks
    
    fig_s = go.Figure()
    uids = df['particle'].unique()
    limit = 100 if not sel else 9999
    for p in uids[:limit]:
        d = df[df['particle'] == p]
        fig_s.add_trace(go.Scatter(x=d['frame'], y=d['intensity_measure'].fillna(0), mode='lines', opacity=0.3 if not sel else 1.0, name=f"{p}"))
    avg = df.groupby('frame')['intensity_measure'].mean().fillna(0)
    fig_s.add_trace(go.Scatter(x=avg.index, y=avg.values, mode='lines', line=dict(color='blue', width=3, dash='dash'), name="AVG"))
    fig_s.update_layout(template="plotly_white", title="Intensity Traces")
    
    hm = df.pivot(index='particle', columns='frame', values='intensity_measure').fillna(0)
    fig_h = go.Figure(data=go.Heatmap(z=hm.values, x=hm.columns, y=hm.index, colorscale='Viridis'))
    fig_h.update_layout(template="plotly_white", title="Heatmap")
    return fig_s, fig_h