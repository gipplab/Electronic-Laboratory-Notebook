from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import pickle
import os
import threading
import json
import traceback
from urllib.parse import parse_qs, unquote
from Lab_Misc.Load_Data import Load_MFP_Path
from Lab_Misc.Load_Data import Load_MFP, Load_MFP_Video
from Lab_Misc.General import get_BasePath
from Lab_Misc import General

from Analysis.models import MFPAnalysis
from Analysis.scripts.Cellpose_Cement import run_cellpose_cement_analysis

app = DjangoDash('MFP_Dashboard')

# =========================================================
# LAYOUT
# =========================================================
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='entry-id'),
    
    # Kickstarter
    dcc.Interval(id='kickstarter', interval=500, max_intervals=1),

    html.Div([
        html.Button("🔄 Reload", id='reload-btn', n_clicks=0, className="btn btn-sm btn-outline-primary"),
        html.Button("🧬 Run AI Analysis", id='run-ai-btn', n_clicks=0, className="btn btn-sm btn-warning", style={'marginLeft': '10px'}),
        html.Span(id='loading-status', style={'marginLeft': '15px', 'fontWeight': 'bold', 'color': '#333'})
    ], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #ddd'}),

    html.Div(id='ai-analysis-status', style={'padding': '10px', 'textAlign': 'center'}),
    html.Div(id='ai-log-output-wrapper', style={'margin': '10px', 'padding': '10px', 'backgroundColor': '#eef2f5', 'borderRadius': '5px', 'maxHeight': '150px', 'overflowY': 'auto', 'fontFamily': 'monospace', 'fontSize': '12px', 'display': 'none'}, children=[
        html.Div(id='ai-log-output')
    ]),
    
    dcc.Interval(id='log-interval', interval=2000, n_intervals=0, disabled=True),

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
                                {'label': ' Brightfield', 'value': 'bf'}
                            ], 
                            value='detect', 
                            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                        ),
                        dcc.Checklist(id='show-markers-toggle', options=[{'label': ' Markers', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '10px'}),
                        
                        dcc.Checklist(id='show-cellpose-toggle', options=[{'label': ' 🧠 AI Masks', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '15px', 'color': 'green', 'fontWeight': 'bold'}),
                    ], style={'marginBottom': '5px'}),
                    
                    dcc.Graph(id='image-plot', style={'height': '35vh'}),
                    
                    dcc.Slider(id='frame-slider', min=0, max=100, value=0, step=1, marks={0:'0'}, tooltip={"placement": "bottom", "always_visible": True})
                ], style={'width': '55%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
                
                # RECHTS
                html.Div([
                    html.Label("Particle ID:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='particle-dropdown', options=[], value=None, clearable=False),
                    
                    html.Div([
                        html.Label("Plot Y-Axis:", style={'fontWeight': 'bold', 'marginTop': '10px', 'marginRight': '10px'}),
                        dcc.RadioItems(
                            id='y-axis-selector', 
                            options=[
                                {'label': ' Intensity', 'value': 'intensity_measure'}, 
                                {'label': ' BF Radius', 'value': 'radius_brightfield'},
                                {'label': ' Fluo Radius', 'value': 'real_size'},
                                {'label': ' 🧠 AI Radius', 'value': 'radius_cellpose'} 
                            ], 
                            value='radius_cellpose', 
                            labelStyle={'display': 'inline-block', 'marginRight': '15px'}
                        )
                    ], style={'marginBottom': '5px'}),

                    dcc.Graph(id='single-intensity-graph', style={'height': '35vh'}),
                    html.Div(id='debug-info', style={'color': 'gray', 'fontSize': '0.8em', 'marginTop': '5px'})
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
            ])
        ]),

        dcc.Tab(label='📊 Global Statistics', value='tab-global', children=[
            html.Div([
                html.Div([
                    html.Label("Global Metric:", style={'fontWeight': 'bold', 'marginRight': '15px'}),
                    dcc.RadioItems(
                        id='global-metric-selector', 
                        options=[
                            {'label': ' Intensity', 'value': 'intensity_measure'}, 
                            {'label': ' AI Radius', 'value': 'radius_cellpose'}
                        ], 
                        value='intensity_measure', 
                        labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                    ),
                ], style={'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px', 'marginBottom': '10px'}),
                
                dcc.Dropdown(id='global-id-filter', options=[], multi=True, placeholder="Filter specific IDs..."),
                
                # 🚨 HIER WURDE DIE HÖHE VON 40vh AUF 70vh GEÄNDERT!
                dcc.Graph(id='global-spaghetti', style={'height': '70vh'}),
                
                dcc.Graph(id='global-heatmap', style={'height': '50vh'}),
            ], style={'padding': '20px'})
        ])
    ])
])

# =========================================================
# DATA LOADING (In-Memory Cache)
# =========================================================
DATA_CACHE = {}

def get_data(entry_id):
    if not entry_id: return None
    try: entry_id = int(entry_id)
    except: pass
    
    # Wenn die Daten bereits im RAM sind, extrem schnell von dort zurückgeben
    if entry_id in DATA_CACHE: 
        return DATA_CACHE[entry_id]
        
    # Um den Arbeitsspeicher zu schonen, leeren wir den Cache, bevor wir ein neues 
    # Video laden. So liegt immer nur maximal 1 Video (das aktuelle) im RAM.
    DATA_CACHE.clear()

    try:
        # 1. Versuche alte Tracks zu laden (nur um die echten Zeitstempel zu klauen)
        try:
            tracks_old = Load_MFP(entry_id)
            if tracks_old is None: tracks_old = pd.DataFrame()
            elif not tracks_old.empty: tracks_old = tracks_old.reset_index(drop=True)
        except:
            tracks_old = pd.DataFrame()

        video_data = Load_MFP_Video(entry_id)
        if not video_data: return None
            
        # 2. Lade neue AI-Daten
        cellpose_data = []
        tracks_ai = pd.DataFrame()
        
        # 🚨 NEU: Lese den Pfad aus der Datenbank und setze ihn (wenn nötig) zusammen
        try:
            analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
            result_path = analysis.Result_Path
            if result_path and not os.path.isabs(result_path):
                cp_path = os.path.join(General.get_BasePath(), result_path)
            else:
                cp_path = result_path
        except:
            cp_path = None
            
        # Fallback, falls in der DB noch nichts sauberes steht
        if not cp_path or not os.path.exists(cp_path):
            video_path = Load_MFP_Path(entry_id)
            if video_path and "01_Videos" in video_path:
                cp_path = video_path.replace("01_Videos", "02_Analysis_Results").rsplit('.', 1)[0] + '.pkl'
            else:
                cp_path = f"/tmp/Cellpose_{entry_id}.pkl" # Fallback
        
        if os.path.exists(cp_path):
            try:
                with open(cp_path, 'rb') as f:
                    cp_dict = pickle.load(f)
                    cellpose_data = cp_dict.get('polymersomes', [])
                    
                # WENN DIE AI-DATEN GETRACKT WURDEN (sie haben eine 'particle' ID)
                if cellpose_data and 'particle' in cellpose_data[0]:
                    tracks_ai = pd.DataFrame(cellpose_data)
                    
                    # Umbenennen, damit der Dashboard-Graph den Radius sofort findet
                    if 'radius' in tracks_ai.columns:
                        tracks_ai = tracks_ai.rename(columns={'radius': 'radius_cellpose'})
                    
                    # Zeitstempel aus den alten Daten klauen (falls vorhanden), sonst Frame-Nummer nutzen
                    if not tracks_old.empty and 'time' in tracks_old.columns:
                        time_map = tracks_old.drop_duplicates('frame').set_index('frame')['time'].to_dict()
                        tracks_ai['time'] = tracks_ai['frame'].map(time_map).fillna(tracks_ai['frame'])
                    else:
                        try:
                            import nd2
                            video_path = Load_MFP_Path(entry_id)
                            with nd2.ND2File(video_path) as f:
                                evs = f.events()
                                if evs and 'Time [s]' in evs[0]:
                                    time_map = {i: ev['Time [s]'] for i, ev in enumerate(evs)}
                                    tracks_ai['time'] = tracks_ai['frame'].map(time_map).fillna(tracks_ai['frame'])
                                else:
                                    tracks_ai['time'] = tracks_ai['frame']
                        except:
                            tracks_ai['time'] = tracks_ai['frame']
            except Exception as e:
                print(f"Fehler beim Laden der Cellpose Daten: {e}")
        
        # 3. ENTSCHEIDUNG: Wer ist der Boss?
        if not tracks_ai.empty:
            tracks = tracks_ai  # 🚀 AI übernimmt die rote Track-Führung!
            print("🚀 Nutze perfekten AI-Mittelpunkte als Hauptdatenquelle!")
        else:
            tracks = tracks_old # 🐢 Fallback auf alte Methode
            print("🐢 Nutze alte Trackpy-Tracks (Keine KI-Daten gefunden).")
            
        if tracks.empty: 
            return None
        
        data = {
            'tracks': tracks,
            'vid_detect': video_data['detect'],
            'vid_measure': video_data['measure'],
            'vid_bf': video_data['brightfield'],
            'cellpose': cellpose_data 
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

@app.callback(
    [Output('ai-analysis-status', 'children'), 
     Output('log-interval', 'disabled'), 
     Output('ai-log-output-wrapper', 'style'),
     Output('ai-log-output', 'children')],
    [Input('run-ai-btn', 'n_clicks'), Input('log-interval', 'n_intervals')],
    [State('entry-id', 'data')]
)
def handle_ai_analysis(n_clicks, n_intervals, entry_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # FALL 1: Der Start-Button wurde gedrückt
    if trigger_id == 'run-ai-btn':
        if n_clicks == 0 or not entry_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        try:
            analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
            dia = getattr(analysis, 'Particle_Diameter', 51)
            minmass = getattr(analysis, 'Threshold', 0.05)
            
            threading.Thread(target=run_cellpose_cement_analysis, args=(entry_id, dia, minmass, None, None, 'all', None)).start()
            
            style = {'margin': '10px', 'padding': '10px', 'backgroundColor': '#eef2f5', 'borderRadius': '5px', 'maxHeight': '150px', 'overflowY': 'auto', 'fontFamily': 'monospace', 'fontSize': '12px', 'display': 'block'}
            return html.Div("🚀 KI-Analyse läuft im Hintergrund...", style={'color': 'blue', 'fontWeight': 'bold'}), False, style, "Warte auf Logdatei..."
        except Exception as e:
            return html.Div(f"❌ Fehler: {str(e)}", style={'color': 'red', 'fontWeight': 'bold'}), dash.no_update, dash.no_update, dash.no_update

    # FALL 2: Das Intervall holt sich neue Log-Updates
    elif trigger_id == 'log-interval':
        if not entry_id: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        log_file = f"/tmp/cellpose_log_{entry_id}.txt"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                log_divs = [html.Div(line, style={'color': 'green' if '✅' in line else ('red' if '❌' in line else ('orange' if '⚠️' in line else 'black')), 'marginBottom': '2px'}) for line in lines if line.strip()]
                text_content = "".join(lines)
                if "✅ Analyse erfolgreich abgeschlossen" in text_content or "❌ Systemfehler" in text_content:
                    status = html.Div("✅ Analyse fertig! Lade die Seite neu (🔄 Reload).", style={'color': 'green', 'fontWeight': 'bold'})
                    return status, True, dash.no_update, log_divs
                else:
                    return dash.no_update, dash.no_update, dash.no_update, log_divs
            except: return dash.no_update, dash.no_update, dash.no_update, html.Div("Lese Logdatei...")
        return dash.no_update, dash.no_update, dash.no_update, html.Div("Warte auf Logdatei...")

@app.callback(
    [Output('entry-id', 'data'), Output('loading-status', 'children'),
     Output('particle-dropdown', 'options'), Output('particle-dropdown', 'value'),
     Output('global-id-filter', 'options'),
     Output('frame-slider', 'max'), Output('frame-slider', 'marks')],
    [Input('url', 'search'), Input('kickstarter', 'n_intervals'), Input('reload-btn', 'n_clicks')],
    [State('entry-id', 'data')]
)
def init_dashboard(search, n, clicks, current_id, **kwargs):
    entry_id = current_id
    
    if not entry_id and search:
        try:
            decoded = unquote(search)
            qs = parse_qs(decoded.lstrip('?'))
            if 'id' in qs: entry_id = qs['id'][0]
            elif 'session_state' in qs:
                state = json.loads(qs['session_state'][0])
                entry_id = state.get('MFP_id') or state.get('id')
        except: pass
        
    # 🚀 Lösung: ID direkt aus dem Django Session State auslesen (via kwargs)
    session_state = kwargs.get('session_state', {})
    if not entry_id and session_state and session_state.get('MFP_id'):
        entry_id = session_state.get('MFP_id')

    if not entry_id: return None, "❌ Keine ID gefunden.", [], None, [], 100, {0:'0'}

    data = get_data(entry_id)
    if not data: return entry_id, f"❌ Keine Daten für ID {entry_id}", [], None, [], 100, {0:'0'}
    
    tracks = data['tracks']
    if tracks.empty: return entry_id, "⚠️ 0 Partikel gefunden.", [], None, [], 100, {0:'0'}

    all_particles = sorted(tracks['particle'].unique().tolist())
    options = [{'label': f"ID {p}", 'value': int(p)} for p in all_particles]
    first_val = int(all_particles[0]) if all_particles else None
    
    mf = int(tracks['frame'].max())
    
    # --- NEU: Zeit-basierte Slider Marks ---
    marks = {}
    if 'time' in tracks.columns and not tracks['time'].empty:
        time_df = tracks.drop_duplicates('frame').sort_values('frame')
        all_times_sec = time_df['time']
        scaled_times, unit = General.get_smart_time(all_times_sec)
        time_map = pd.Series(scaled_times.values, index=time_df['frame']).to_dict()
        
        # ~10 Ticks für den Slider
        for i in np.linspace(0, mf, 11, dtype=int):
            i_int = int(i)
            scaled_t = time_map.get(i_int)
            if scaled_t is not None:
                marks[i_int] = f'{int(scaled_t)}{unit[0]}'
        
        marks[0] = 'Start'
        if mf in time_map:
            marks[mf] = f'{int(time_map[mf])}{unit[0]}'
        else:
            marks[mf] = 'Ende'
    else:
        marks = {0: 'Start', mf: 'Ende'}
    
    return entry_id, f"✅ ID {entry_id} geladen ({len(all_particles)} Partikel).", options, first_val, options, mf, marks


@app.callback(
    [Output('image-plot', 'figure'), Output('single-intensity-graph', 'figure'), Output('debug-info', 'children')],
    [Input('frame-slider', 'value'), Input('channel-selector', 'value'), 
     Input('particle-dropdown', 'value'), Input('show-markers-toggle', 'value'),
     Input('show-cellpose-toggle', 'value'), 
     Input('y-axis-selector', 'value')], 
    [State('entry-id', 'data')]
)
def update_view(frame, channel, pid, markers, show_cellpose, y_metric, entry_id):
    if not entry_id: return go.Figure(), go.Figure(), ""
    data = get_data(entry_id)
    if not data or data['vid_detect'] is None: 
        return go.Figure(layout={'title': "Video not found"}), go.Figure(), "Video Missing"

    tracks = data['tracks']
    
    if channel == 'bf':
        vid = data.get('vid_bf', data['vid_detect'])
        cmap = 'gray'
    elif channel == 'measure':
        vid = data['vid_measure']
        cmap = 'inferno'
    else:
        vid = data['vid_detect']
        cmap = 'viridis'
    
    if frame >= len(vid): frame = len(vid)-1
    
    # --- BILD (HEATMAP) ---
    fig_img = go.Figure()
    fig_img.add_trace(go.Heatmap(z=vid[frame], colorscale=cmap, showscale=False, hoverinfo='skip'))
    
    try:
        shapes = []
        scatter_x, scatter_y, scatter_text, scatter_colors, scatter_hover = [], [], [], [], []

        cp_this_frame = []
        if data.get('cellpose'):
            cp_this_frame = [p for p in data['cellpose'] if p.get('frame') == frame]
            for cp in cp_this_frame:
                if 'show' in show_cellpose:
                    is_valid = cp['valid']
                    col = '#00FF00' if is_valid else '#8B0000'
                    r = cp['radius']
                    shapes.append(dict(
                        type="circle", xref="x", yref="y",
                        x0=cp['x']-r, y0=cp['y']-r, x1=cp['x']+r, y1=cp['y']+r,
                        line=dict(color=col, width=2, dash='solid' if is_valid else 'dot')
                    ))

        # --- TRACKPY MARKER & IDs ---
        if 'show' in markers and not tracks.empty:
            curr_tracks = tracks[tracks['frame'] == frame]
            for _, row in curr_tracks.iterrows():
                p_id = int(row['particle'])
                cx, cy = row['x'], row['y']
                
                # Radius-Suche für Hover (großzügig 250px)
                found_rad = "N/A"
                if cp_this_frame:
                    dists = [(np.sqrt((p['x']-cx)**2 + (p['y']-cy)**2), p['radius']) for p in cp_this_frame if p['valid']]
                    if dists:
                        d_min, r_val = min(dists, key=lambda x: x[0])
                        if d_min < 250: 
                            found_rad = f"{r_val:.1f}px"

                is_selected = (pid is not None) and (p_id == int(pid))
                color = '#00FFFF' if is_selected else '#FFFF00'
                
                shapes.append(dict(
                    type="path", path=f"M {cx-4},{cy-4} L {cx+4},{cy+4} M {cx-4},{cy+4} L {cx+4},{cy-4}",
                    line=dict(color="red", width=2)
                ))
                
                scatter_x.append(cx)
                scatter_y.append(cy)
                scatter_text.append(f"ID {p_id}")
                scatter_colors.append(color)
                scatter_hover.append(f"<b>ID {p_id}</b><br>X: {cx:.1f} | Y: {cy:.1f}<br>AI-Rad: {found_rad}")

        fig_img.update_layout(shapes=shapes)
        if scatter_x:
            fig_img.add_trace(go.Scatter(
                x=scatter_x, y=scatter_y, mode='text', text=scatter_text,
                textposition='top right', textfont=dict(color=scatter_colors, size=12, family="Arial Black"),
                hoverinfo='text', hovertext=scatter_hover, showlegend=False
            ))

    except Exception as e:
        print(f"Update Error: {e}")

    h, w = vid[frame].shape
    fig_img.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=650, title=f"Frame {frame}",
                          xaxis=dict(range=[0, w], visible=False), 
                          yaxis=dict(autorange='reversed', scaleanchor="x", scaleratio=1, visible=False))

    # --- GRAPH LOGIK ---
    fig_graph = go.Figure()
    current_txt = "Select particle..."
    
    if pid is not None:
        t_data = tracks[tracks['particle'] == int(pid)].sort_values('frame')
        time_vals, t_unit = General.get_smart_time(t_data['time'])
        frame_vals = t_data['frame']
        
        # SMART MAPPING MIT RADIUS-GEDÄCHTNIS
        if y_metric == 'radius_cellpose':
            y_values = []
            mem_rad = None # Das Gedächtnis
            
            for _, r in t_data.iterrows():
                f, rx, ry = r['frame'], r['x'], r['y']
                
                # Startwert für das Gedächtnis festlegen, falls noch leer
                if mem_rad is None:
                    mem_rad = r.get('real_size', 25)
                    if pd.isna(mem_rad) or mem_rad == 0:
                        mem_rad = r.get('radius_brightfield', 25)
                    if pd.isna(mem_rad) or mem_rad == 0:
                        mem_rad = 25
                        
                best = None
                if data.get('cellpose'):
                    hits = [p for p in data['cellpose'] if p['frame'] == f and p['valid']]
                    if hits:
                        hits.sort(key=lambda p: np.sqrt((p['x']-rx)**2 + (p['y']-ry)**2))
                        for h in hits:
                            dist = np.sqrt((h['x']-rx)**2 + (h['y']-ry)**2)
                            
                            # DIE ZWEI-STUFEN REGEL:
                            if dist <= 40: 
                                # Nah -> Sofort nehmen, es ist sicher unsere Zelle
                                best = h['radius']
                                break
                            elif dist <= 250 and abs(h['radius'] - mem_rad) <= 25: 
                                # Weit gesprungen -> Prüfe zwingend, ob der Radius ähnlich geblieben ist!
                                best = h['radius']
                                break
                                
                if best is not None: 
                    mem_rad = best # Aktualisiere das Gedächtnis mit dem neu gefundenen Radius
                    
                y_values.append(best)
        else:
            y_values = t_data[y_metric].fillna(0).tolist() if y_metric in t_data.columns else [0] * len(t_data)

        # connectgaps=True sorgt für durchgehende Linien, auch wenn die KI kurz geblinzelt hat
        fig_graph.add_trace(go.Scatter(x=time_vals, y=y_values, mode='lines+markers', 
                                      name=f"ID {pid}", connectgaps=True))

        # Roter, halbtransparenter Punkt für den aktuellen Frame
        curr = t_data[t_data['frame'] == frame]
        if not curr.empty:
            idx = t_data.index.get_loc(curr.index[0])
            val = y_values[idx]
            t_scaled = time_vals.iloc[idx]
            if val is not None and not pd.isna(val):
                fig_graph.add_trace(go.Scatter(x=[t_scaled], y=[val], mode='markers',
                                              marker=dict(color='rgba(255,0,0,0.5)', size=14, line=dict(color='red', width=2)),
                                              name="Current"))
                current_txt = f"ID {pid} | {t_scaled:.2f}{t_unit} | Val: {val:.1f}"

        # Zweite X-Achse für Frame-Nummern hinzufügen
        num_ticks = 10
        if len(time_vals) > 1:
            tick_indices = np.linspace(0, len(time_vals) - 1, num_ticks, dtype=int)
            tickvals_time = time_vals.iloc[tick_indices].tolist()
            ticktext_frame = frame_vals.iloc[tick_indices].tolist()
        else:
            tickvals_time = time_vals.tolist()
            ticktext_frame = frame_vals.tolist()

        fig_graph.update_layout(
            template="plotly_white", 
            xaxis_title=f"Time ({t_unit})", 
            yaxis_title=y_metric,
            margin=dict(t=50), # Verhindert, dass die Achse abgeschnitten wird
            xaxis2=dict(
                title="Frame Number", overlaying='x', side='top', matches='x', # Zwingt die Achse zum Mitlaufen
                tickvals=tickvals_time, ticktext=ticktext_frame
            )
        )
    return fig_img, fig_graph, current_txt

@app.callback(
    Output('frame-slider', 'value'),
    [Input('single-intensity-graph', 'clickData')],
    [State('entry-id', 'data'), State('particle-dropdown', 'value')],
    prevent_initial_call=True
)
def jump_to_frame_on_click(clickData, entry_id, pid):
    if not clickData or not entry_id or not pid:
        return dash.no_update

    try:
        # 1. Geklickten Zeitwert holen
        clicked_time_scaled = clickData['points'][0]['x']

        # 2. Daten für das aktuelle Partikel laden
        data = get_data(entry_id)
        if not data: return dash.no_update
        tracks = data['tracks']
        t_data = tracks[tracks['particle'] == int(pid)].sort_values('frame')
        if t_data.empty: return dash.no_update

        # 3. Zeitachse neu skalieren, um die Skala des Graphen zu treffen
        time_vals_scaled, _ = General.get_smart_time(t_data['time'])

        # 4. Index des nächstgelegenen Zeitwerts finden und Frame-Nummer zurückgeben
        closest_index = np.abs(time_vals_scaled.values - clicked_time_scaled).argmin()
        return int(t_data.iloc[closest_index]['frame'])
    except:
        return dash.no_update

@app.callback(
    [Output('global-spaghetti', 'figure'), Output('global-heatmap', 'figure')],
    [Input('global-id-filter', 'value'), 
     Input('global-metric-selector', 'value'), # 🚨 NEU: Der Metrik-Umschalter
     Input('tabs', 'value')],
    [State('entry-id', 'data')]
)
def update_glob(sel, metric, tab, eid):
    if tab != 'tab-global' or not eid: return dash.no_update, dash.no_update
    data = get_data(eid)
    if not data: return go.Figure(), go.Figure()
    
    tracks = data['tracks'].copy() # Wichtig: Kopie erstellen, um Original-Cache nicht zu ändern
    cellpose_data = data.get('cellpose', [])
    
    # Sicherstellen, dass die Spalte existiert (AI Radius ist manchmal noch 'radius')
    col = metric
    if col not in tracks.columns and col == 'radius_cellpose' and 'radius' in tracks.columns:
        col = 'radius'

    # --- NEU: On-the-fly Berechnung für AI Radius, falls nötig ---
    if metric == 'radius_cellpose' and cellpose_data and 'radius_cellpose' not in tracks.columns:
        cp_lookup = {}
        for p in cellpose_data:
            if p.get('valid', False):
                frame = p['frame']
                if frame not in cp_lookup: cp_lookup[frame] = []
                cp_lookup[frame].append(p)

        def map_radius_for_particle(particle_group):
            y_values = []
            mem_rad = None
            particle_group = particle_group.sort_values('frame')

            for _, r in particle_group.iterrows():
                f, rx, ry = r['frame'], r['x'], r['y']
                
                if mem_rad is None:
                    mem_rad = r.get('real_size', 25)
                    if pd.isna(mem_rad) or mem_rad == 0: mem_rad = r.get('radius_brightfield', 25)
                    if pd.isna(mem_rad) or mem_rad == 0: mem_rad = 25
                
                best = None
                if f in cp_lookup:
                    hits = cp_lookup[f]
                    hits.sort(key=lambda p: np.sqrt((p['x'] - rx)**2 + (p['y'] - ry)**2))
                    for h in hits:
                        dist = np.sqrt((h['x'] - rx)**2 + (h['y'] - ry)**2)
                        if dist <= 40: best = h['radius']; break
                        elif dist <= 250 and abs(h['radius'] - mem_rad) <= 25: best = h['radius']; break
                
                if best is not None: mem_rad = best
                y_values.append(best)
            
            particle_group['radius_cellpose'] = y_values
            return particle_group

        tracks = tracks.groupby('particle').apply(map_radius_for_particle).reset_index(drop=True)
        col = 'radius_cellpose'
        
    df = tracks[tracks['particle'].isin(sel)].copy() if sel else tracks.copy()
    scaled_time, t_unit = General.get_smart_time(df['time'])
    df['scaled_time'] = scaled_time
    
    # --- SPAGHETTI PLOT ---
    fig_s = go.Figure()
    uids = df['particle'].unique()
    limit = 100 if not sel else 9999
    
    for p in uids[:limit]:
        d = df[df['particle'] == p].sort_values('time')
        t_vals = d['scaled_time']
        
        y_vals = d[col].fillna(0) if col in d.columns else [0] * len(d)
        fig_s.add_trace(go.Scatter(
            x=t_vals, 
            y=y_vals, 
            mode='lines', 
            opacity=0.3 if not sel else 1.0, 
            name=f"ID {p}",
            hovertemplate=f"ID {p}<br>Time: %{{x:.2f}}{t_unit}<br>Val: %{{y:.1f}}"
        ))
    
    # Durchschnittslinie (AVG)
    if col in df.columns:
        avg = df.groupby('frame').agg({'scaled_time': 'first', col: 'mean'})
    else:
        avg = df.groupby('frame').agg({'scaled_time': 'first'})
        avg[col] = 0

    avg_t = avg['scaled_time']
    avg_frames = avg.index
    
    fig_s.add_trace(go.Scatter(
        x=avg_t, y=avg[col], 
        mode='lines', line=dict(color='black', width=3, dash='dash'), name="AVG"
    ))
    
    # Zweite X-Achse für Frame-Nummern
    num_ticks = 10
    num_points = len(avg_t)
    if num_points > 1:
        tick_indices = np.linspace(0, num_points - 1, min(num_ticks, num_points), dtype=int)
        tickvals_time = avg_t.iloc[tick_indices].tolist()
        ticktext_frame = avg_frames[tick_indices].to_list()
    else:
        tickvals_time = avg_t.tolist()
        ticktext_frame = avg_frames.to_list()

    title_suffix = "Intensity (A.U.)" if col == 'intensity_measure' else "Radius (px)"
    fig_s.update_layout(
        template="plotly_white", 
        title=f"Global Traces: {title_suffix}",
        xaxis_title=f"Time ({t_unit})",
        yaxis_title=title_suffix,
        margin=dict(t=60),
        xaxis2=dict(
            title="Frame Number", overlaying='x', side='top', matches='x', 
            tickvals=tickvals_time, ticktext=ticktext_frame
        )
    )
    
    # --- HEATMAP ---

    # Pivot-Tabelle für die Heatmap erstellen
    if col in df.columns:
        hm = df.pivot(index='particle', columns='frame', values=col).fillna(0)
    else:
        hm = pd.DataFrame(0, index=uids, columns=df['frame'].unique())
    
    fig_h = go.Figure(data=go.Heatmap(
        z=hm.values, 
        x=hm.columns, 
        y=hm.index, 
        colorscale='Viridis' if col == 'intensity_measure' else 'Cividis',
        colorbar=dict(title=title_suffix)
    ))
    
    fig_h.update_layout(
        template="plotly_white", 
        title=f"Heatmap: {title_suffix} per Frame", 
        xaxis_title="Frame Number",
        yaxis_title="Particle ID"
    )
    
    return fig_s, fig_h