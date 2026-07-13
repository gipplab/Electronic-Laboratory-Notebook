from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import pickle
import os
import threading
import json
import traceback
from scipy.stats import spearmanr
from urllib.parse import parse_qs, unquote

from Lab_Misc.Load_Data import Load_MFP_Path, Load_MFP, Load_MFP_Video
from Lab_Misc import General
from Exp_Main.models import MFP as Main_MFP
from Analysis.models import MFPAnalysis
from Analysis.scripts.Cellpose_Cement import run_cellpose_cement_analysis

app = DjangoDash('MFP_Dashboard')

# =========================================================
# LAYOUT-BLÖCKE
# =========================================================
tab_single_ui = html.Div([
    html.Div([
        html.Div([
            html.Label("Channel:", style={'fontWeight': 'bold'}),
            dcc.RadioItems(id='channel-selector', options=[{'label': ' Detect', 'value': 'detect'}, {'label': ' Measure', 'value': 'measure'}, {'label': ' BF', 'value': 'bf'}], value='detect', labelStyle={'display': 'inline-block', 'marginRight': '10px'}),
            dcc.Checklist(id='show-markers-toggle', options=[{'label': ' Markers', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '10px'}),
            dcc.Checklist(id='show-cellpose-toggle', options=[{'label': ' 🧠 AI Masks', 'value': 'show'}], value=['show'], style={'display': 'inline-block', 'marginLeft': '15px', 'color': 'green', 'fontWeight': 'bold'}),
        ], style={'marginBottom': '5px'}),
        dcc.Graph(id='image-plot', style={'height': '35vh'}),
        dcc.Slider(id='frame-slider', min=0, max=100, value=0, step=1, marks={0:'0'}, tooltip={"placement": "bottom", "always_visible": True})
    ], style={'width': '55%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
    
    html.Div([
        html.Label("Particle ID:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(id='particle-dropdown', options=[], value=None, clearable=False),
        html.Div([
            html.Label("Plot Y-Axis:", style={'fontWeight': 'bold', 'marginTop': '10px', 'marginRight': '10px'}),
            dcc.RadioItems(id='y-axis-selector', options=[
                {'label': ' Total Int. Measure (🔴)', 'value': 'intensity_measure'}, 
                {'label': ' Mean Int. Measure (🔴)', 'value': 'mean_intensity_measure'}, 
                {'label': ' Total Int. Detect (🟢)', 'value': 'intensity_detect'}, 
                {'label': ' Mean Int. Detect (🟢)', 'value': 'mean_intensity_detect'}, 
                {'label': ' BF Radius', 'value': 'radius_brightfield'},
                {'label': ' Fluo Radius', 'value': 'real_size'},
                {'label': ' 🧠 AI Radius', 'value': 'radius_cellpose'},
                {'label': ' 📈 Growth (µm)', 'value': 'cum_norm_growth_um'}
            ], value='radius_cellpose', labelStyle={'display': 'inline-block', 'marginRight': '15px'})
        ], style={'marginBottom': '5px'}),
        dcc.Graph(id='single-intensity-graph', style={'height': '35vh'}),
        html.Div(id='debug-info', style={'color': 'gray', 'fontSize': '0.8em', 'marginTop': '5px'})
    ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
])

tab_global_ui = html.Div([
    html.Div([
        html.Label("Global Metric:", style={'fontWeight': 'bold', 'marginRight': '15px'}),
        dcc.RadioItems(id='global-metric-selector', options=[
            {'label': ' Total Int. Measure (🔴)', 'value': 'intensity_measure'}, 
            {'label': ' Mean Int. Measure (🔴)', 'value': 'mean_intensity_measure'}, 
            {'label': ' Total Int. Detect (🟢)', 'value': 'intensity_detect'}, 
            {'label': ' Mean Int. Detect (🟢)', 'value': 'mean_intensity_detect'}, 
            {'label': ' AI Radius', 'value': 'radius_cellpose'},
            {'label': ' 📈 Growth (µm)', 'value': 'cum_norm_growth_um'}
        ], value='cum_norm_growth_um', labelStyle={'display': 'inline-block', 'marginRight': '20px'}),
        dcc.Checklist(id='threshold-filter', options=[{'label': ' 🚀 Nur Partikel > 0.3 µm Wachstum', 'value': 'filter'}], value=[], style={'display': 'inline-block', 'marginLeft': '20px', 'fontWeight': 'bold', 'color': 'red'})
    ], style={'padding': '10px', 'backgroundColor': '#f1f3f5', 'borderRadius': '5px', 'marginBottom': '10px'}),
    dcc.Dropdown(id='global-id-filter', options=[], multi=True, placeholder="Filter specific IDs..."),
    dcc.Graph(id='global-spaghetti', style={'height': '65vh'}),
    html.Div(id='excluded-audit-log', style={'marginTop': '20px', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderTop': '2px solid #dee2e6', 'borderRadius': '5px'}),
    dcc.Graph(id='global-heatmap', style={'height': '50vh', 'marginTop': '20px'}),
], style={'padding': '20px'})

tab_scatter_ui = html.Div([
    html.Div([
        html.H4("Volume Change vs. Norm. Total mScarlet Expression", style={'textAlign': 'center', 'fontWeight': 'bold', 'marginBottom': '15px'}),
        dcc.Graph(id='scatter-growth-expression', style={'height': '75vh'})
    ], style={'padding': '20px'})
])

app.layout = html.Div([
    html.Div([
        html.Button("🔄 Reload", id='reload-btn', n_clicks=0, className="btn btn-sm btn-outline-primary"),
        html.Button("🧬 Run AI Analysis", id='run-ai-btn', n_clicks=0, className="btn btn-sm btn-warning", style={'marginLeft': '10px'}),
        html.Button("⚙️ Settings", id='toggle-settings-btn', n_clicks=0, className="btn btn-sm btn-info", style={'marginLeft': '10px'}),
        html.Span(id='loading-status', style={'marginLeft': '15px', 'fontWeight': 'bold', 'color': '#333'})
    ], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #ddd'}),

    html.Div(id='settings-panel', style={'display': 'none', 'padding': '15px', 'backgroundColor': '#e9ecef', 'textAlign': 'center', 'borderBottom': '1px solid #ccc'}, children=[
        html.Div([html.Label("Min. Radius Cut-off (px):", style={'marginRight': '5px', 'fontWeight': 'bold'}), dcc.Input(id='input-radius', type='number', value=40, style={'width': '80px'})], style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Div([html.Label("Exclude IDs (z.B. 4, 12):", style={'marginRight': '5px', 'fontWeight': 'bold'}), dcc.Input(id='input-exclude', type='text', placeholder="4, 12", style={'width': '120px'})], style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Div([html.Label("Connect IDs (z.B. 1:2):", style={'marginRight': '5px', 'fontWeight': 'bold'}), dcc.Input(id='input-connect', type='text', placeholder="1:2, 4:5", style={'width': '150px'})], style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Button("💾 Save & Apply", id='save-settings-btn', n_clicks=0, className="btn btn-sm btn-success"),
        html.Div(id='settings-msg', style={'color': 'green', 'fontWeight': 'bold', 'marginTop': '5px'})
    ]),

    dcc.Location(id='url', refresh=False), 
    dcc.Store(id='entry-id'),
    dcc.Store(id='refresh-trigger', data=0), 
    
    dcc.Interval(id='kickstarter', interval=500, max_intervals=1),
    html.Div(id='ai-analysis-status', style={'padding': '10px', 'textAlign': 'center'}),
    html.Div(id='ai-log-output-wrapper', style={'margin': '10px', 'padding': '10px', 'backgroundColor': '#eef2f5', 'borderRadius': '5px', 'maxHeight': '150px', 'overflowY': 'auto', 'fontFamily': 'monospace', 'fontSize': '12px', 'display': 'none'}, children=[html.Div(id='ai-log-output')]),
    dcc.Interval(id='log-interval', interval=2000, n_intervals=0, disabled=True),

    dcc.Tabs(id='tabs', value='tab-single', children=[
        dcc.Tab(label='🔎 Single Inspection', value='tab-single', children=[tab_single_ui]),
        dcc.Tab(label='📊 Global Statistics', value='tab-global', children=[tab_global_ui]),
        dcc.Tab(label='📈 Growth vs. Expression', value='tab-scatter', children=[tab_scatter_ui])
    ])
])

# =========================================================
# DATA LOADING 
# =========================================================
DATA_CACHE = {}

def get_data(entry_id, force_reload=False):
    if not entry_id: return None
    try: entry_id = int(entry_id)
    except: pass
    if entry_id in DATA_CACHE and not force_reload: return DATA_CACHE[entry_id]
    DATA_CACHE.clear()
    
    try:
        try: tracks_old = Load_MFP(entry_id)
        except: tracks_old = pd.DataFrame()
        if tracks_old is None: tracks_old = pd.DataFrame()
        elif not tracks_old.empty: tracks_old = tracks_old.reset_index(drop=True)

        video_data = Load_MFP_Video(entry_id)
        if not video_data: return None
            
        cellpose_data, tracks_ai = [], pd.DataFrame()
        try: cp_path = os.path.join(General.get_BasePath(), MFPAnalysis.objects.get(Entry_id=entry_id).Result_Path)
        except: cp_path = None
        if not cp_path or not os.path.exists(cp_path):
            vp = Load_MFP_Path(entry_id)
            cp_path = vp.replace("01_Videos", "02_Analysis_Results").rsplit('.', 1)[0] + '.pkl' if vp and "01_Videos" in vp else f"/tmp/Cellpose_{entry_id}.pkl" 
        
        if os.path.exists(cp_path):
            try:
                with open(cp_path, 'rb') as f: cellpose_data = pickle.load(f).get('polymersomes', [])
                if cellpose_data and 'particle' in cellpose_data[0]:
                    tracks_ai = pd.DataFrame(cellpose_data).rename(columns={'radius': 'radius_cellpose'}, errors='ignore')
                    if not tracks_old.empty and 'time' in tracks_old.columns:
                        tracks_ai['time'] = tracks_ai['frame'].map(tracks_old.drop_duplicates('frame').set_index('frame')['time'].to_dict()).fillna(tracks_ai['frame'])
                    else: tracks_ai['time'] = tracks_ai['frame']
            except: pass
        
        tracks = tracks_ai if not tracks_ai.empty else tracks_old
        if tracks.empty: return None
        
        img_h, img_w = video_data['detect'][0].shape if video_data.get('detect') is not None else (2448, 2048)
        best_rad_col = next((r for r in ['radius_cellpose', 'real_size', 'radius_brightfield', 'radius'] if r in tracks.columns), None)
        
        if best_rad_col:
            dash_exp = Main_MFP.objects.get(id=int(entry_id)).Dash if Main_MFP.objects.filter(id=int(entry_id)).exists() else None
            try: default_cutoff = float(MFPAnalysis.objects.get(Entry_id=int(entry_id)).Threshold)
            except: default_cutoff = 40.0
            tracks = General.process_mfp_tracks(tracks, dash_exp, best_rad_col, img_w, img_h, default_cutoff)

        DATA_CACHE[int(entry_id)] = {'tracks': tracks, 'vid_detect': video_data['detect'], 'vid_measure': video_data['measure'], 'vid_bf': video_data['brightfield'], 'cellpose': cellpose_data}
        return DATA_CACHE[int(entry_id)]
    except Exception as e:
        print(f"Error in get_data: {e}\n{traceback.format_exc()}")
        return None

# =========================================================
# CALLBACKS (Race-Condition Fix)
# =========================================================
@app.callback(Output('settings-panel', 'style'), [Input('toggle-settings-btn', 'n_clicks')], [State('settings-panel', 'style')])
def toggle_settings(n_clicks, current_style):
    if n_clicks == 0: return current_style
    current_style['display'] = 'block' if current_style.get('display') == 'none' else 'none'
    return current_style

# 🚨 MASTER SYNC CALLBACK: Regelt Laden, Speichern UND GUI Update strikt in einer Linie!
@app.callback(
    [Output('entry-id', 'data'), Output('loading-status', 'children'), Output('particle-dropdown', 'options'), Output('particle-dropdown', 'value'), 
     Output('global-id-filter', 'options'), Output('frame-slider', 'max'), Output('frame-slider', 'marks'), 
     Output('refresh-trigger', 'data'), Output('settings-msg', 'children'), Output('input-radius', 'value'), Output('input-exclude', 'value'), Output('input-connect', 'value')],
    [Input('url', 'search'), Input('kickstarter', 'n_intervals'), Input('reload-btn', 'n_clicks'), Input('save-settings-btn', 'n_clicks')], 
    [State('entry-id', 'data'), State('refresh-trigger', 'data'), State('input-radius', 'value'), State('input-exclude', 'value'), State('input-connect', 'value')]
)
def master_sync(search, kick_n, reload_clicks, save_clicks, entry_id, refresh_val, r_val, exc_val, conn_val, **kwargs):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''

    # 1. ID identifizieren
    if not entry_id and search:
        try: entry_id = parse_qs(unquote(search).lstrip('?')).get('id', [None])[0] or json.loads(parse_qs(unquote(search).lstrip('?')).get('session_state', ['{}'])[0]).get('MFP_id')
        except: pass
    if not entry_id: entry_id = kwargs.get('session_state', {}).get('MFP_id')
    if not entry_id: return dash.no_update, "❌ Keine ID", [], None, [], 100, {0:'0'}, dash.no_update, "", 40, "", ""

    # 2. Speichern in DB & Cache erzwingen
    force_reload = False
    msg = ""
    dash_exp = Main_MFP.objects.get(id=int(entry_id)).Dash if Main_MFP.objects.filter(id=int(entry_id)).exists() else None

    if trigger == 'save-settings-btn' and dash_exp:
        dash_exp.Radius_Cutoff, dash_exp.Excluded_IDs, dash_exp.Connected_IDs = float(r_val or 40.0), str(exc_val or ""), str(conn_val or "")
        dash_exp.save()
        force_reload, msg = True, "✅ Saved & Applied!"
    elif trigger == 'reload-btn':
        force_reload, msg = True, "✅ Reloaded!"

    # 3. Sauberes Laden der geforderten / aktualisierten Daten
    data = get_data(entry_id, force_reload=force_reload)

    # 4. Settings Panel Werte aktualisieren
    db_r = dash_exp.Radius_Cutoff if dash_exp and dash_exp.Radius_Cutoff and float(dash_exp.Radius_Cutoff) > 0 else getattr(MFPAnalysis.objects.filter(Entry_id=int(entry_id)).first(), 'Threshold', 40.0)
    db_exc, db_conn = (dash_exp.Excluded_IDs or "", dash_exp.Connected_IDs or "") if dash_exp else ("", "")

    if not data or data['tracks'].empty: return entry_id, "⚠️ Keine Partikel.", [], None, [], 100, {0:'0'}, (refresh_val or 0) + 1, msg, db_r, db_exc, db_conn

    # 5. Dropdown Optionen generieren
    tracks = data['tracks']
    all_p = sorted(tracks['particle'].unique().tolist(), key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else x)
    options = [{'label': f"ID {p}" if tracks[tracks['particle']==p]['status'].iloc[0]=='Valid' else f"ID {p} (⚠️ {tracks[tracks['particle']==p]['status'].iloc[0]})", 'value': p} for p in all_p]
    
    mf = int(tracks['frame'].max())
    marks = {0: 'Start', mf: 'Ende'}
    if 'time' in tracks.columns and not tracks['time'].empty:
        time_df = tracks.drop_duplicates('frame').sort_values('frame')
        scaled_times, unit = General.get_smart_time(time_df['time'])
        time_map = pd.Series(scaled_times.values, index=time_df['frame']).to_dict()
        marks = {int(i): f'{int(time_map[int(i)])}{unit[0]}' for i in np.linspace(0, mf, 11, dtype=int) if int(i) in time_map}
        marks.update({0: 'Start', mf: f'{int(time_map[mf])}{unit[0]}' if mf in time_map else 'Ende'})
        
    val_count = len(tracks[tracks['status'] == 'Valid']['particle'].unique())
    load_stat = f"✅ Geladen ({val_count} Valid | {len(all_p)-val_count} Ignoriert)."

    # 6. TRIGGER FEUERN (Damit sich die Graphen nach dem Update zeichnen!)
    return entry_id, load_stat, options, all_p[0] if all_p else None, options, mf, marks, (refresh_val or 0) + 1, msg, db_r, db_exc, db_conn


@app.callback(
    [Output('ai-analysis-status', 'children'), Output('log-interval', 'disabled'), Output('ai-log-output-wrapper', 'style'), Output('ai-log-output', 'children')],
    [Input('run-ai-btn', 'n_clicks'), Input('log-interval', 'n_intervals')], [State('entry-id', 'data')]
)
def handle_ai_analysis(n_clicks, n_intervals, entry_id):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'run-ai-btn':
        if n_clicks == 0 or not entry_id: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        try:
            analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
            threading.Thread(target=run_cellpose_cement_analysis, args=(entry_id, getattr(analysis, 'Particle_Diameter', 51), getattr(analysis, 'Threshold', 0.05), None, None, 'all', None)).start()
            return html.Div("🚀 KI-Analyse läuft...", style={'color': 'blue', 'fontWeight': 'bold'}), False, {'margin': '10px', 'padding': '10px', 'backgroundColor': '#eef2f5', 'borderRadius': '5px', 'maxHeight': '150px', 'overflowY': 'auto', 'fontFamily': 'monospace', 'fontSize': '12px', 'display': 'block'}, "Warte auf Log..."
        except Exception as e: return html.Div(f"❌ Fehler: {str(e)}", style={'color': 'red'}), dash.no_update, dash.no_update, dash.no_update

    elif trigger_id == 'log-interval':
        if not entry_id: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        log_file = f"/tmp/cellpose_log_{entry_id}.txt"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f: lines = f.readlines()
                log_divs = [html.Div(line, style={'color': 'green' if '✅' in line else ('red' if '❌' in line else ('orange' if '⚠️' in line else 'black')), 'marginBottom': '2px'}) for line in lines if line.strip()]
                if "✅ Analyse erfolgreich" in "".join(lines) or "❌ Systemfehler" in "".join(lines):
                    return html.Div("✅ Analyse fertig! Lade neu (🔄 Reload).", style={'color': 'green', 'fontWeight': 'bold'}), True, dash.no_update, log_divs
                return dash.no_update, dash.no_update, dash.no_update, log_divs
            except: return dash.no_update, dash.no_update, dash.no_update, html.Div("Lese Log...")
        return dash.no_update, dash.no_update, dash.no_update, html.Div("Warte auf Logdatei...")


# 🚨 Die folgenden 3 Plot-Funktionen reagieren jetzt NUR NOCH auf den refresh-trigger (und Tabs)
@app.callback(
    [Output('image-plot', 'figure'), Output('single-intensity-graph', 'figure'), Output('debug-info', 'children')],
    [Input('frame-slider', 'value'), Input('channel-selector', 'value'), Input('particle-dropdown', 'value'), Input('show-markers-toggle', 'value'), Input('show-cellpose-toggle', 'value'), Input('y-axis-selector', 'value'), Input('tabs', 'value'), Input('refresh-trigger', 'data')],
    [State('entry-id', 'data')]
)
def update_view(frame, channel, pid, markers, show_cellpose, y_metric, tab, refresh_trigger, entry_id):
    if tab != 'tab-single': return dash.no_update, dash.no_update, dash.no_update
    if not entry_id or not get_data(entry_id): return go.Figure(), go.Figure(), "No Data"
    
    data = get_data(entry_id)
    tracks, vid = data['tracks'], data.get('vid_bf', data['vid_detect']) if channel == 'bf' else (data['vid_measure'] if channel == 'measure' else data['vid_detect'])
    if frame >= len(vid): frame = len(vid)-1
    
    fig_img = go.Figure(go.Heatmap(z=vid[frame], colorscale='gray' if channel=='bf' else ('inferno' if channel=='measure' else 'viridis'), showscale=False, hoverinfo='skip'))
    shapes, sx, sy, stxt, scol, shov = [], [], [], [], [], []
    cp_frame = [p for p in data['cellpose'] if p.get('frame') == frame] if data.get('cellpose') else []
    
    for cp in cp_frame:
        if 'show' in show_cellpose: shapes.append(dict(type="circle", xref="x", yref="y", x0=cp['x']-cp['radius'], y0=cp['y']-cp['radius'], x1=cp['x']+cp['radius'], y1=cp['y']+cp['radius'], line=dict(color='#00FF00' if cp['valid'] else '#8B0000', width=2, dash='solid' if cp['valid'] else 'dot')))

    if 'show' in markers and not tracks.empty:
        for _, row in tracks[tracks['frame'] == frame].iterrows():
            p_id, cx, cy, stat = str(row['particle']), row['x'], row['y'], row['status']
            f_rad = f"{min([(np.sqrt((p['x']-cx)**2 + (p['y']-cy)**2), p['radius']) for p in cp_frame if p['valid']], key=lambda x:x[0])[1]:.1f}px" if cp_frame and min([(np.sqrt((p['x']-cx)**2 + (p['y']-cy)**2), p['radius']) for p in cp_frame if p['valid']], key=lambda x:x[0])[0] < 250 else "N/A"
            shapes.append(dict(type="path", path=f"M {cx-4},{cy-4} L {cx+4},{cy+4} M {cx-4},{cy+4} L {cx+4},{cy-4}", line=dict(color="red" if stat == 'Valid' else "gray", width=2)))
            sx.append(cx); sy.append(cy); stxt.append(f"ID {p_id}")
            scol.append('#00FFFF' if str(pid)==p_id else ('#FFFF00' if stat == 'Valid' else '#808080'))
            shov.append(f"<b>ID {p_id}</b><br>Status: {stat}<br>X: {cx:.1f} | Y: {cy:.1f}<br>AI-Rad: {f_rad}")

    fig_img.update_layout(shapes=shapes, margin=dict(l=0,r=0,t=30,b=0), height=650, title=f"Frame {frame}", xaxis=dict(range=[0, vid[frame].shape[1]], visible=False), yaxis=dict(autorange='reversed', scaleanchor="x", scaleratio=1, visible=False))
    if sx: fig_img.add_trace(go.Scatter(x=sx, y=sy, mode='text', text=stxt, textposition='top right', textfont=dict(color=scol, size=12, family="Arial Black"), hoverinfo='text', hovertext=shov, showlegend=False))

    fig_graph = go.Figure()
    if pid is not None:
        t_data = tracks[tracks['particle'] == str(pid)].sort_values('frame')
        time_vals, t_unit = General.get_smart_time(t_data['time'])
        y_values = t_data[y_metric].fillna(0).tolist() if y_metric in t_data.columns else [0]*len(t_data)
        
        if y_metric == 'radius_cellpose' and data.get('cellpose'):
            y_values, mem = [], None 
            for _, r in t_data.iterrows():
                f, rx, ry = r['frame'], r['x'], r['y']
                mem = r.get('real_size', 25) if mem is None else mem
                best = next((h['radius'] for h in sorted([p for p in data['cellpose'] if p['frame']==f and p['valid']], key=lambda p: np.sqrt((p['x']-rx)**2 + (p['y']-ry)**2)) if np.sqrt((h['x']-rx)**2 + (h['y']-ry)**2) <= 40 or (np.sqrt((h['x']-rx)**2 + (h['y']-ry)**2) <= 250 and abs(h['radius']-mem)<=25)), None)
                if best is not None: mem = best
                y_values.append(best)

        fig_graph.add_trace(go.Scatter(x=time_vals, y=y_values, mode='lines+markers', name=f"ID {pid}", connectgaps=True))
        if not t_data[t_data['frame'] == frame].empty:
            idx = t_data.index.get_loc(t_data[t_data['frame'] == frame].index[0])
            if y_values[idx] is not None and not pd.isna(y_values[idx]): fig_graph.add_trace(go.Scatter(x=[time_vals.iloc[idx]], y=[y_values[idx]], mode='markers', marker=dict(color='rgba(255,0,0,0.5)', size=14, line=dict(color='red', width=2)), name="Current"))
        
        t_title = "Cumulative Norm. Growth (µm)" if y_metric == 'cum_norm_growth_um' else ("Intensity" if 'intensity' in y_metric else y_metric)
        fig_graph.update_layout(template="plotly_white", xaxis_title=f"Time ({t_unit})", yaxis_title=t_title, margin=dict(t=50))
    return fig_img, fig_graph, "Select particle..."

@app.callback(Output('frame-slider', 'value'), [Input('single-intensity-graph', 'clickData')], [State('entry-id', 'data'), State('particle-dropdown', 'value')], prevent_initial_call=True)
def jump(clickData, entry_id, pid):
    if not clickData or not entry_id or not pid or not get_data(entry_id): return dash.no_update
    t_data = get_data(entry_id)['tracks'][get_data(entry_id)['tracks']['particle'] == str(pid)].sort_values('frame')
    return int(t_data.iloc[np.abs(General.get_smart_time(t_data['time'])[0].values - clickData['points'][0]['x']).argmin()]['frame']) if not t_data.empty else dash.no_update

@app.callback(
    [Output('global-spaghetti', 'figure'), Output('global-heatmap', 'figure'), Output('excluded-audit-log', 'children')],
    [Input('global-id-filter', 'value'), Input('global-metric-selector', 'value'), Input('threshold-filter', 'value'), Input('tabs', 'value'), Input('refresh-trigger', 'data')], [State('entry-id', 'data')]
)
def update_glob(sel, metric, threshold_filter, tab, refresh_trigger, eid):
    if tab != 'tab-global': return dash.no_update, dash.no_update, dash.no_update
    if not eid or not get_data(eid): return go.Figure(), go.Figure(), html.Div("Keine Daten geladen.")
    
    tracks = get_data(eid)['tracks'].copy() 
    col = metric if metric in tracks.columns else ('radius' if metric == 'radius_cellpose' and 'radius' in tracks.columns else metric)

    df = tracks[tracks['particle'].isin(sel)].copy() if sel else tracks.copy()
    if 'filter' in threshold_filter and 'cum_norm_growth_um' in df.columns:
        valid_growth = df.groupby('particle')['cum_norm_growth_um'].max()
        df = df[df['particle'].isin(valid_growth[valid_growth > 0.3].index)]
        if df.empty: return go.Figure(layout={'title': "All filtered (Growth < 0.3 µm)"}), go.Figure(), ""

    scaled_time, t_unit = General.get_smart_time(df['time'])
    fig_s = go.Figure()
    
    for p in df['particle'].unique()[:100 if not sel else 9999]:
        d, stat = df[df['particle'] == p].sort_values('time'), df[df['particle'] == p]['status'].iloc[0]
        fig_s.add_trace(go.Scatter(x=scaled_time[d.index], y=d[col].fillna(0) if col in d.columns else [0]*len(d), mode='lines', opacity=0.4 if stat!='Valid' else (0.3 if not sel else 1.0), line=dict(color='lightgray' if stat!='Valid' else None, dash='dot' if stat!='Valid' else 'solid'), name=f"ID {p}" if stat=='Valid' else f"ID {p} ({stat})", hovertemplate=f"<b>ID {p}</b><br>Status: {stat}<br>Val: %{{y:.2f}}"))
    
    if not df[df['status'] == 'Valid'].empty:
        avg = df[df['status'] == 'Valid'].groupby('frame').agg({'time': 'first', col: 'mean' if col in df[df['status'] == 'Valid'].columns else lambda x: 0})
        fig_s.add_trace(go.Scatter(x=General.get_smart_time(avg['time'])[0], y=avg[col], mode='lines', line=dict(color='black', width=3, dash='dash'), name="AVG (Nur Valide)"))
    
    ts = "Cumulative Norm. Growth (µm)" if col == 'cum_norm_growth_um' else ("Intensity" if 'intensity' in col else "Radius (px)")
    fig_s.update_layout(template="plotly_white", title=f"Global Traces: {ts}", xaxis_title=f"Time ({t_unit})", yaxis_title=ts, margin=dict(t=60))
    
    hm_df = df[df['status'] == 'Valid'] if not df[df['status'] == 'Valid'].empty else df
    fig_h = go.Figure(data=go.Heatmap(z=(hm_df.pivot(index='particle', columns='frame', values=col).fillna(0) if col in hm_df.columns else pd.DataFrame(0, index=df['particle'].unique(), columns=df['frame'].unique())).values, x=hm_df['frame'].unique(), y=hm_df['particle'].unique(), colorscale='Viridis' if 'intensity' in col else 'Cividis', colorbar=dict(title=ts)))
    fig_h.update_layout(template="plotly_white", title=f"Heatmap: {ts} per Frame (Nur Valide)", xaxis_title="Frame Number", yaxis_title="Particle ID")
    
    df_ex = df[df['status'] != 'Valid'].drop_duplicates(subset=['particle'])
    audit_ui = html.Div([html.H5("✨ Audit-Log: Keine Partikel ignoriert", style={'color': 'green', 'margin': 0})]) if df_ex.empty else html.Div([html.H5(f"⚠️ Audit-Log: {len(df_ex)} Partikel im Graphen ignoriert (grau gestrichelt)", style={'marginBottom': '10px', 'color': '#333'}), html.Table([html.Tr([html.Th("Partikel ID", style={'width': '20%'}), html.Th("Grund für Ausschluss", style={'width': '80%'})])] + [html.Tr([html.Td(f"ID {row['particle']}", style={'fontWeight': 'bold'}), html.Td(row['status'], style={'color': '#d9534f'})]) for _, row in df_ex.iterrows()], className="table table-sm table-striped table-bordered", style={'backgroundColor': 'white', 'marginBottom': 0})])
    
    return fig_s, fig_h, audit_ui

@app.callback(
    Output('scatter-growth-expression', 'figure'),
    [Input('global-id-filter', 'value'), Input('tabs', 'value'), Input('refresh-trigger', 'data')], [State('entry-id', 'data')]
)
def update_scatter(sel, tab, refresh_trigger, eid):
    if tab != 'tab-scatter': return dash.no_update
    if not eid or not get_data(eid): return go.Figure(layout={'title': "Keine Daten geladen."})
    
    tracks = get_data(eid)['tracks'].copy()
    df = tracks[tracks['particle'].isin(sel)].copy() if sel else tracks.copy()
    df = df[df['status'] == 'Valid'] 
    
    if df.empty or 'norm_total_intensity' not in df.columns:
        return go.Figure(layout={'title': "Keine ausreichenden / validen Intensitäts-Daten gefunden."})
        
    stats = []
    for p_id, group in df.groupby('particle'):
        min_g = group['cum_norm_growth_um'].min()
        max_g = group['cum_norm_growth_um'].max()
        extreme_g = min_g if abs(min_g) > abs(max_g) else max_g
        max_int = group['norm_total_intensity'].max()
        
        if pd.notna(extreme_g) and pd.notna(max_int):
            stats.append({'Particle_ID': p_id, 'Extreme_Growth_um': extreme_g, 'Max_Norm_Total_Intensity': max_int})
            
    res_df = pd.DataFrame(stats).dropna()
    if res_df.empty: return go.Figure(layout={'title': "Keine berechenbaren Werte."})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=res_df['Extreme_Growth_um'], y=res_df['Max_Norm_Total_Intensity'],
        mode='markers+text', text=res_df['Particle_ID'], textposition="top right",
        marker=dict(size=12, color='#1f77b4', line=dict(width=1, color='black')),
        name=f"PK {eid}"
    ))

    if len(res_df) > 1:
        m, b = np.polyfit(res_df['Extreme_Growth_um'], res_df['Max_Norm_Total_Intensity'], 1)
        x_range = np.array([res_df['Extreme_Growth_um'].min(), res_df['Extreme_Growth_um'].max()])
        fig.add_trace(go.Scatter(x=x_range, y=m * x_range + b, mode='lines', line=dict(color='black', width=2), name="Global Trend"))

    sp_r, sp_p = spearmanr(res_df['Extreme_Growth_um'], res_df['Max_Norm_Total_Intensity'])

    fig.add_vline(x=0.3, line_dash="dash", line_color="blue", annotation_text="Growth > +0.3")
    fig.add_vline(x=-0.3, line_dash="dash", line_color="red", annotation_text="Shrink < -0.3")
    fig.add_vline(x=0, line_color="gray", line_width=1)

    fig.update_layout(
        template="plotly_white",
        title=f"Spearman r: {sp_r:.3f} (p-value: {sp_p:.2e})",
        xaxis_title="Extreme Cumulative Normalized Change (µm)<br><-- Shrinking | Growing -->",
        yaxis_title="Max Norm. Total Intensity (A.U.)",
        height=700
    )
    
    return fig