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

from Lab_Misc.Load_Data import Load_MFP, Load_MFP_Video
from Lab_Misc.General import get_BasePath
from Lab_Misc import General


from Analysis.models import MFPAnalysis

app = DjangoDash('MFP_Dashboard')

# =========================================================
# LAYOUT
# =========================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='entry-id'),
    
    # Kickstarter
    dcc.Interval(id='kickstarter', interval=500, max_intervals=1),

    html.H2("MFP Analysis Dashboard", style={'textAlign': 'center', 'fontFamily': 'sans-serif'}),
    
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
                        dcc.RadioItems(
                            id='channel-selector', 
                            options=[
                                {'label': ' Detection', 'value': 'detect'}, 
                                {'label': ' Measure', 'value': 'measure'},
                                {'label': ' Brightfield', 'value': 'bf'} # NEU: Brightfield Option
                            ], 
                            value='detect', 
                            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                        ),
                        dcc.Checklist(id='show-markers-toggle', options=[{'label': ' Markers', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '10px'}),
                    ], style={'marginBottom': '5px'}),
                    
                    dcc.Graph(id='image-plot', style={'height': '65vh'}),
                    
                    dcc.Slider(id='frame-slider', min=0, max=100, value=0, step=1, marks={0:'0'}, tooltip={"placement": "bottom", "always_visible": True})
                ], style={'width': '55%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
                
                # RECHTS
                html.Div([
                    html.Label("Particle ID:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='particle-dropdown', options=[], value=None, clearable=False),
                    
                    # --- NEU: Schalter für die Y-Achse ---
                    html.Div([
                        html.Label("Plot Y-Axis:", style={'fontWeight': 'bold', 'marginTop': '10px', 'marginRight': '10px'}),
                        dcc.RadioItems(
                            id='y-axis-selector', 
                            options=[
                                {'label': ' Intensity', 'value': 'intensity_measure'}, 
                                {'label': ' BF Radius', 'value': 'radius_brightfield'},
                                {'label': ' Fluo Radius', 'value': 'real_size'}
                            ], 
                            value='radius_brightfield', # Start-Einstellung
                            labelStyle={'display': 'inline-block', 'marginRight': '15px'}
                        )
                    ], style={'marginBottom': '5px'}),
                    # ------------------------------------

                    dcc.Graph(id='single-intensity-graph', style={'height': '45vh'}),
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
        # 1. TABELLE LADEN
        tracks = Load_MFP(entry_id)
        if tracks.empty: 
            return None

        tracks = tracks.reset_index(drop=True)

        # 2. VIDEO LADEN (Nutzt jetzt die neue Funktion in Load_Data.py)
        video_data = Load_MFP_Video(entry_id)
        
        if not video_data:
            print(f"Video data could not be loaded for {entry_id}")
            return None
        
        # Alles zusammenpacken für den Cache
        data = {
            'tracks': tracks,
            'vid_detect': video_data['detect'],
            'vid_measure': video_data['measure'],
            'vid_bf': video_data['brightfield']
        }
        
        DATA_CACHE[entry_id] = data
        return data

    except Exception as e:
        print(f"Error in get_data: {e}")
        return None

    except Exception as e:
        print(f"Error in get_data: {e}")
        traceback.print_exc()
        return None

# =========================================================
# CALLBACKS
# =========================================================

@app.callback(
    [Output('entry-id', 'data'), Output('loading-status', 'children'),
     Output('particle-dropdown', 'options'), Output('particle-dropdown', 'value'),
     Output('global-id-filter', 'options'),
     Output('frame-slider', 'max'), Output('frame-slider', 'marks')],
    [Input('url', 'search'), Input('kickstarter', 'n_intervals'), Input('reload-btn', 'n_clicks')]
)
def init_dashboard(search, n, clicks):
    entry_id = None
    if search:
        try:
            decoded = unquote(search)
            qs = parse_qs(decoded.lstrip('?'))
            if 'id' in qs: entry_id = qs['id'][0]
            elif 'session_state' in qs:
                state = json.loads(qs['session_state'][0])
                entry_id = state.get('MFP_id') or state.get('id')
        except: pass

    if not entry_id: return None, "❌ Keine ID gefunden.", [], None, [], 100, {0:'0'}

    data = get_data(entry_id)
    if not data: return entry_id, f"❌ Keine Daten für ID {entry_id}", [], None, [], 100, {0:'0'}
    
    tracks = data['tracks']
    if tracks.empty: return entry_id, "⚠️ 0 Partikel gefunden.", [], None, [], 100, {0:'0'}

    all_particles = sorted(tracks['particle'].unique())
    options = [{'label': f"ID {p}", 'value': p} for p in all_particles]
    first_val = all_particles[0] if all_particles else None
    
    mf = int(tracks['frame'].max())
    marks = {0: 'Start', mf: 'Ende'}
    
    return entry_id, f"✅ ID {entry_id} geladen ({len(all_particles)} Partikel).", options, first_val, options, mf, marks


@app.callback(
    [Output('image-plot', 'figure'), Output('single-intensity-graph', 'figure'), Output('debug-info', 'children')],
    [Input('frame-slider', 'value'), Input('channel-selector', 'value'), 
     Input('particle-dropdown', 'value'), Input('show-markers-toggle', 'value'),
     Input('y-axis-selector', 'value')], # <--- NEU HINZUGEFÜGT
    [State('entry-id', 'data')]
)
def update_view(frame, channel, pid, markers, y_metric, entry_id): # <--- y_metric hinzugefügt!
    if not entry_id: return go.Figure(), go.Figure(), ""
    data = get_data(entry_id)
    if not data or data['vid_detect'] is None: 
        return go.Figure(layout={'title': "Video not found"}), go.Figure(), "Video Missing"

    tracks = data['tracks']
    
    # NEU: Video und Colormap anhand des gewählten Kanals bestimmen
    if channel == 'bf':
        vid = data.get('vid_bf', data['vid_detect']) # Fallback falls bf fehlt
        cmap = 'gray'
    elif channel == 'measure':
        vid = data['vid_measure']
        cmap = 'inferno'
    else:
        vid = data['vid_detect']
        cmap = 'viridis'
    
    if frame >= len(vid): frame = len(vid)-1
    
    # --- 1. BILD (HEATMAP) ---
    fig_img = go.Figure()
    fig_img.add_trace(go.Heatmap(z=vid[frame], colorscale=cmap, showscale=False, hoverinfo='skip'))
    
    # --- 2. KREISE (SHAPES) & TEXT-LABELS ---
    try:
        shapes = []
        scatter_x = []
        scatter_y = []
        scatter_text = []
        scatter_hover = []
        scatter_colors = []

        if 'show' in markers:
            df = tracks[tracks['frame'] == frame]
            if not df.empty:
                for _, row in df.iterrows():
                    p_id = int(row['particle'])
                    is_sel = (pid is not None) and (p_id == int(pid))
                    
                    # --- NEU: ZENTRUM UND RADIUS DYNAMISCH WÄHLEN ---
                    # Wenn wir den Brightfield-Radius haben, nutzen wir auch das 
                    # korrigierte Brightfield-Zentrum (falls vorhanden)
                    if 'radius_brightfield' in row and pd.notna(row['radius_brightfield']):
                        r_px = row['radius_brightfield']
                        is_valid = row.get('radius_brightfield_valid', True)
                        
                        # Nutze bf_center_x/y wenn vorhanden, sonst nimm das alte Fluo-Zentrum (x/y)
                        center_x = row.get('bf_center_x', row['x'])
                        center_y = row.get('bf_center_y', row['y'])
                        
                        # Sicherheitscheck für NaN-Werte im Zentrum
                        if pd.isna(center_x) or pd.isna(center_y):
                            center_x, center_y = row['x'], row['y']
                    else:
                        r_px = row.get('real_size', 5.0) 
                        is_valid = row.get('valid_fit', True)
                        center_x = row['x']
                        center_y = row['y']

                    col = '#00FFFF' if is_sel else ('red' if is_valid else 'orange')
                    lw = 3 if is_sel else 1.5
                    style = 'solid' if is_valid else 'dot'

                    # Shapes dem Layout hinzufügen (mit den neuen Zentren!)
                    shapes.append(dict(
                        type="circle",
                        xref="x", yref="y",
                        x0 = center_x - r_px,
                        y0 = center_y - r_px,
                        x1 = center_x + r_px,
                        y1 = center_y + r_px,
                        line = dict(color=col, width=lw, dash=style)
                    ))
                    
                    # Daten für Text/Hover sammeln (auch auf neuem Zentrum)
                    scatter_x.append(center_x)
                    scatter_y.append(center_y)
                    scatter_text.append(f"<b>{p_id}</b>")
                    scatter_hover.append(f"ID: {p_id}<br>Radius: {r_px:.1f}px")
                    scatter_colors.append(col)
        
        # 1. Shapes ins Layout packen
        fig_img.update_layout(shapes=shapes)

        # 2. Text und Hover-Layer als unsichtbaren Scatter hinzufügen
        if scatter_x:
            fig_img.add_trace(go.Scatter(
                x=scatter_x,
                y=scatter_y,
                mode='text',
                text=scatter_text,
                textposition='top right',
                textfont=dict(color=scatter_colors, size=14),
                hoverinfo='text',
                hovertext=scatter_hover,
                showlegend=False
            ))

    except Exception as e:
        print(f"Shape Error: {e}")
        traceback.print_exc()
        
    # --- BILD-PROPORTIONEN FIXIEREN ---
    img_height, img_width = vid[frame].shape

    fig_img.update_layout(
        margin=dict(l=0, r=0, t=30, b=0), 
        height=600, 
        title=f"Frame {frame}",
        # Achsen passend zum Bild definieren
        xaxis=dict(range=[0, img_width], showgrid=False, zeroline=False, visible=False), 
        # autorange='reversed' ist oft sicherer als [img_height, 0], um Konflikte mit Heatmap/Scatter zu vermeiden!
        yaxis=dict(autorange='reversed', scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, visible=False),
        clickmode='event+select'
    )
    
    # --- 3. GRAPH ---
    fig_graph = go.Figure()
    txt = "Select a particle..."
    
    if pid is not None:
        try: pid = int(pid)
        except: pass
        
        # Daten für das gewählte Partikel holen
        t_data = tracks[tracks['particle'] == pid].sort_values('frame')
        
        # 1. ZENTRALE SKALIERUNG BERECHNEN
        # Wir rufen die Funktion für den ganzen Datensatz auf, um die Einheit (t_unit) zu bestimmen
        time_vals, t_unit = General.get_smart_time(t_data['time'])
        
        # Den Skalierungsfaktor manuell festlegen, damit wir ihn auf Einzelwerte anwenden können
        if t_unit == "h":
            scale_factor = 3600.0
        elif t_unit == "min":
            scale_factor = 60.0
        else:
            scale_factor = 1.0
            
        y_values = t_data[y_metric].fillna(0)
        
        # Achsen-Labels
        metric_labels = {
            'intensity_measure': 'Intensity (A.U.)',
            'radius_brightfield': 'Brightfield Radius (px)',
            'real_size': 'Fluorescence Radius (px)'
        }
        y_label = metric_labels.get(y_metric, 'Value')
        
        # Die Linie plotten (mit den bereits skalierten time_vals)
        fig_graph.add_trace(go.Scatter(x=time_vals, y=y_values, mode='lines+markers', name=f"ID {pid}"))
        
        # 2. ROTER PUNKT (CURRENT FRAME)
        curr = t_data[t_data['frame'] == frame]
        if not curr.empty:
            val = curr[y_metric].fillna(0).values[0]
            
            # HIER WAR DER FEHLER: Wir erzwingen den gleichen Skalierungsfaktor wie oben!
            c_time_raw = curr['time'].values[0]
            c_time_scaled = c_time_raw / scale_factor
            
            # Info Text zusammenbauen
            int_val = curr.get('intensity_measure', [0]).values[0]
            r_bf = curr.get('radius_brightfield', [0]).values[0]
            txt = f"ID {pid} | {c_time_scaled:.2f} {t_unit} | Int: {int_val:.0f} | BF-Rad: {r_bf:.1f}px"
            
            # Jetzt wird der Punkt exakt auf der skalierten X-Achse gezeichnet
            fig_graph.add_trace(go.Scatter(
                x=[c_time_scaled], 
                y=[val], 
                mode='markers', 
                marker=dict(color='red', size=12, line=dict(color='white', width=2)), 
                name="Current"
            ))
        
        fig_graph.update_layout(
            yaxis_title=y_label, 
            xaxis_title=f"Time ({t_unit})",
            template="plotly_white",
            title=txt
        )
    
    return fig_img, fig_graph, txt
    

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
    
    # Einheit für die gesamte Gruppe bestimmen
    _, t_unit = General.get_smart_time(df['time'])
    
    fig_s = go.Figure()
    uids = df['particle'].unique()
    limit = 100 if not sel else 9999
    
    for p in uids[:limit]:
        d = df[df['particle'] == p].sort_values('time')
        # Zeit für dieses Partikel skalieren
        t_vals, _ = General.get_smart_time(d['time'])
        
        fig_s.add_trace(go.Scatter(
            x=t_vals, 
            y=d['intensity_measure'].fillna(0), 
            mode='lines', 
            opacity=0.3 if not sel else 1.0, 
            name=f"{p}"
        ))
    
    # Durchschnittslinie (AVG)
    # Hier gruppieren wir nach gerundeten Zeiten oder wir nutzen weiterhin Frames für die Berechnung
    avg = df.groupby('frame').agg({'time': 'first', 'intensity_measure': 'mean'})
    avg_t, _ = General.get_smart_time(avg['time'])
    
    fig_s.add_trace(go.Scatter(
        x=avg_t, y=avg['intensity_measure'], 
        mode='lines', line=dict(color='black', width=3, dash='dash'), name="AVG"
    ))
    
    fig_s.update_layout(
        template="plotly_white", 
        title=f"Intensity Traces ({t_unit})",
        xaxis_title=f"Time ({t_unit})",
        yaxis_title="Intensity (A.U.)"
    )
    
    # Heatmap (Hier bleiben wir bei Frames auf der X-Achse, da sie ein fixes Raster brauchen)
    hm = df.pivot(index='particle', columns='frame', values='intensity_measure').fillna(0)
    fig_h = go.Figure(data=go.Heatmap(z=hm.values, x=hm.columns, y=hm.index, colorscale='Viridis'))
    fig_h.update_layout(template="plotly_white", title="Heatmap (by Frame)", xaxis_title="Frame Number")
    
    return fig_s, fig_h