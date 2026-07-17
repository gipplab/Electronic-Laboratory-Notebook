from django_plotly_dash import DjangoDash
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import threading
import uuid
import traceback
from scipy.stats import spearmanr
from django.db import close_old_connections

from Lab_Misc.Load_Data import Load_MFP, Load_MFP_Video
from Lab_Misc import General
from Exp_Main.models import MFP as Main_MFP
from Analysis.models import MFPAnalysis

app = DjangoDash('MFP_Daily_Dashboard')

def get_available_dates():
    try:
        dates = Main_MFP.objects.exclude(Date_time__isnull=True).dates('Date_time', 'day')
        return sorted([d.strftime('%Y-%m-%d') for d in dates], reverse=True)
    except:
        return []

app.layout = html.Div([
    dcc.Store(id='current-task'), 
    dcc.Interval(id='progress-interval', interval=1000, n_intervals=0, disabled=True), 
    
    html.Div([
        html.H3("📅 Daily Growth vs. Expression", style={'textAlign': 'center', 'fontWeight': 'bold', 'marginBottom': '15px'}),
        
        # 🚨 STEUERUNGS-LEISTE: Datum & Y-Achsen Dropdowns
        html.Div([
            html.Div([
                html.Label("Datum:", style={'fontWeight': 'bold', 'marginRight': '5px'}),
                dcc.Dropdown(
                    id='date-dropdown',
                    options=[{'label': d, 'value': d} for d in get_available_dates()],
                    value=get_available_dates()[0] if get_available_dates() else None,
                    style={'width': '160px', 'display': 'inline-block', 'textAlign': 'left'},
                    clearable=False
                ),
            ], style={'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label("Y-Achse (Metric):", style={'fontWeight': 'bold', 'marginRight': '5px'}),
                dcc.Dropdown(
                    id='y-metric-dropdown',
                    options=[
                        {'label': '⚡ Total Intensity (Absolut)', 'value': 'total_intensity'},
                        {'label': '⚖️ Norm. Total Intensity (Relativ zu Start)', 'value': 'norm_total_intensity'},
                        {'label': '🔴 Mean Intensity (Measure Kanal)', 'value': 'mean_intensity_measure'},
                        {'label': '🟢 Mean Intensity (Detect Kanal)', 'value': 'mean_intensity_detect'},
                    ],
                    value='total_intensity',
                    style={'width': '300px', 'display': 'inline-block', 'textAlign': 'left'},
                    clearable=False
                ),
            ], style={'display': 'inline-block'}),
        ], style={'textAlign': 'center', 'marginBottom': '15px'}),
        
        html.Div([
            html.Progress(id='progress-bar', value=0, max=100, style={'width': '50%', 'display': 'none', 'height': '20px'}),
            html.Div(id='progress-text', style={'textAlign': 'center', 'fontWeight': 'bold', 'marginTop': '5px', 'minHeight': '24px'})
        ], style={'textAlign': 'center', 'marginBottom': '15px'}),
        
        dcc.Graph(id='daily-scatter-plot', style={'height': '75vh'})
    ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'})
])

# =========================================================
# HINTERGRUND-LOGIK & THREADING
# =========================================================
PROGRESS_CACHE = {}

def load_and_process_experiment(entry_id, y_metric):
    """Gibt den DataFrame zurück UND prüft, ob die geforderte Y-Spalte existiert."""
    try:
        tracks = Load_MFP(entry_id)
        if tracks is None or tracks.empty: 
            return None, "Datei leer oder nicht gefunden"
            
        best_rad_col = next((r for r in ['radius_cellpose', 'real_size', 'radius_brightfield', 'radius'] if r in tracks.columns), None)
        if not best_rad_col: 
            return None, "Keine Radius-Spalte"
        
        try:
            exp_obj = Main_MFP.objects.get(id=int(entry_id))
            dash_exp = getattr(exp_obj, 'Dash', None)
        except:
            dash_exp = None
            
        try: 
            default_cutoff = float(MFPAnalysis.objects.get(Entry_id=int(entry_id)).Threshold)
        except: 
            default_cutoff = 40.0
        
        img_h, img_w = tracks.attrs.get('resolution', (2304, 2304))
        
        try:
            tracks = General.process_mfp_tracks(tracks, dash_exp, best_rad_col, img_w, img_h, default_cutoff)
        except Exception as e:
            return None, f"General.py Fehler: {str(e)}"
            
        valid_tracks = tracks[tracks['status'] == 'Valid']
        if valid_tracks.empty:
            return None, "Alle Partikel herausgefiltert"
            
        # 🚨 Prüfen, ob die im Dropdown gewählte Metrik im DataFrame existiert
        if y_metric not in valid_tracks.columns:
            return None, f"Spalte '{y_metric}' fehlt in diesen Daten"
            
        return valid_tracks, "OK"
        
    except Exception as e:
        return None, f"Unbekannter Fehler: {str(e)}"

def process_daily_data_async(selected_date, y_metric, task_id):
    close_old_connections() 
    try:
        PROGRESS_CACHE[task_id] = {'progress': 0, 'total': 1, 'status': 'Suche Experimente...', 'done': False, 'fig': go.Figure(), 'msg': ''}
        
        exps_on_day = Main_MFP.objects.filter(Date_time__date=selected_date)
        exp_ids = list(exps_on_day.values_list('id', flat=True))
        
        if not exp_ids:
            PROGRESS_CACHE[task_id].update({'done': True, 'msg': f"Keine Experimente am {selected_date}.", 'fig': go.Figure()})
            return
            
        total_exps = len(exp_ids)
        stats = []
        fail_log = {} 
        
        for i, eid in enumerate(exp_ids):
            PROGRESS_CACHE[task_id].update({'progress': i, 'status': f'Verarbeite ID {eid} ({i+1}/{total_exps})...'})
            
            df, status_msg = load_and_process_experiment(eid, y_metric)
            
            if df is None:
                fail_log[status_msg] = fail_log.get(status_msg, 0) + 1
                continue
                
            for p_id, group in df.groupby('particle'):
                if 'cum_norm_growth_um' not in group.columns or y_metric not in group.columns:
                    continue
                    
                min_g = group['cum_norm_growth_um'].min()
                max_g = group['cum_norm_growth_um'].max()
                extreme_g = min_g if abs(min_g) > abs(max_g) else max_g
                
                # 🚨 Zieht dynamisch den Max-Wert der im Dropdown gewählten Spalte!
                max_int = group[y_metric].max()
                
                if pd.notna(extreme_g) and pd.notna(max_int):
                    stats.append({
                        'Experiment_ID': str(eid),
                        'Particle_ID': p_id,
                        'Extreme_Growth_um': extreme_g,
                        'Max_Intensity': max_int
                    })
        
        PROGRESS_CACHE[task_id].update({'progress': total_exps, 'status': 'Zeichne Diagramm...'})
        
        res_df = pd.DataFrame(stats).dropna()
        if res_df.empty:
            err_details = " | ".join([f"{k}: {v}x" for k, v in fail_log.items()])
            fail_str = f"Fehlschläge: {err_details}" if fail_log else "Keine auswertbaren Partikel gefunden."
            PROGRESS_CACHE[task_id].update({'done': True, 'msg': f"❌ Keine validen Daten. {fail_str}", 'fig': go.Figure(layout={'title': "Keine Daten."})})
            return

        fig = go.Figure()
        unique_exps = res_df['Experiment_ID'].unique()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for idx, exp_id in enumerate(unique_exps):
            exp_data = res_df[res_df['Experiment_ID'] == exp_id]
            fig.add_trace(go.Scatter(
                x=exp_data['Extreme_Growth_um'], y=exp_data['Max_Intensity'],
                mode='markers+text', text=exp_data['Particle_ID'], textposition="top right",
                marker=dict(size=12, color=colors[idx % len(colors)], line=dict(width=1, color='black')),
                name=f"Exp {exp_id}"
            ))

        if len(res_df) > 1:
            m, b = np.polyfit(res_df['Extreme_Growth_um'], res_df['Max_Intensity'], 1)
            x_range = np.array([res_df['Extreme_Growth_um'].min(), res_df['Extreme_Growth_um'].max()])
            fig.add_trace(go.Scatter(x=x_range, y=m * x_range + b, mode='lines', line=dict(color='black', width=2), name="Daily Trend"))

        sp_r, sp_p = spearmanr(res_df['Extreme_Growth_um'], res_df['Max_Intensity'])
        
        fig.add_vline(x=0.3, line_dash="dash", line_color="blue", annotation_text="Growth > +0.3")
        fig.add_vline(x=-0.3, line_dash="dash", line_color="red", annotation_text="Shrink < -0.3")
        fig.add_vline(x=0, line_color="gray", line_width=1)

        # Lesbare Titel für die Y-Achse
        y_title_map = {
            'total_intensity': 'Max Total Intensity (A.U.)',
            'norm_total_intensity': 'Max Norm. Total Intensity (Relativ zu Start)',
            'mean_intensity_measure': 'Max Mean Intensity Measure 🔴 (A.U./px)',
            'mean_intensity_detect': 'Max Mean Intensity Detect 🟢 (A.U./px)'
        }
        y_label = y_title_map.get(y_metric, y_metric)

        fig.update_layout(
            template="plotly_white",
            title=f"<b>{selected_date}</b> | Spearman r: {sp_r:.3f} (p-value: {sp_p:.2e}) | n={len(res_df)} Partikel",
            xaxis_title="Extreme Cumulative Normalized Change (µm)<br><-- Shrinking | Growing -->",
            yaxis_title=y_label,
            height=700
        )
        
        success_msg = f"✅ Erfolgreich: {len(res_df)} Partikel aus {len(unique_exps)} Experimenten geladen."
        if fail_log:
            success_msg += f" (Ignoriert: {', '.join([f'{k}: {v}x' for k, v in fail_log.items()])})"
            
        PROGRESS_CACHE[task_id].update({'done': True, 'msg': success_msg, 'fig': fig})
        
    except Exception as e:
        err_msg = f"❌ Fehler: {str(e)}"
        traceback.print_exc()
        PROGRESS_CACHE[task_id].update({'done': True, 'msg': err_msg, 'fig': go.Figure()})
    finally:
        close_old_connections()


# =========================================================
# CALLBACK (Reagiert jetzt auf Datum UND Y-Metric Dropdown)
# =========================================================
@app.callback(
    [Output('current-task', 'data'), Output('progress-interval', 'disabled'), Output('progress-bar', 'style'), 
     Output('progress-bar', 'value'), Output('progress-text', 'children'), Output('daily-scatter-plot', 'figure')],
    [Input('date-dropdown', 'value'), Input('y-metric-dropdown', 'value'), Input('progress-interval', 'n_intervals')],
    [State('current-task', 'data')]
)
def manage_loading_state(selected_date, y_metric, n_intervals, task_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 🚨 Reagiert, wenn das Datum ODER das Y-Achsen-Dropdown geändert wird!
    if trigger_id in ['date-dropdown', 'y-metric-dropdown']:
        if not selected_date or not y_metric:
            return None, True, {'display': 'none'}, 0, "", go.Figure()
            
        new_task_id = str(uuid.uuid4())
        threading.Thread(target=process_daily_data_async, args=(selected_date, y_metric, new_task_id)).start()
        
        return new_task_id, False, {'display': 'inline-block', 'width': '50%'}, 0, html.Span("Starte Analyse...", style={'color': '#0d6efd'}), go.Figure(layout={'title': "Lade Daten..."})
        
    elif trigger_id == 'progress-interval':
        if not task_id or task_id not in PROGRESS_CACHE:
            return dash.no_update, True, {'display': 'none'}, 0, "", dash.no_update
            
        status_info = PROGRESS_CACHE[task_id]
        
        if status_info['done']:
            fig = status_info['fig']
            msg = status_info['msg']
            del PROGRESS_CACHE[task_id] 
            msg_ui = html.Span(msg, style={'color': 'green' if '✅' in msg else 'red'})
            return dash.no_update, True, {'display': 'none'}, 100, msg_ui, fig
            
        progress_val = int((status_info['progress'] / max(1, status_info['total'])) * 100)
        msg_ui = html.Span(status_info['status'], style={'color': '#0d6efd'})
        return dash.no_update, False, {'display': 'inline-block', 'width': '50%'}, progress_val, msg_ui, dash.no_update