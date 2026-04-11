from django_plotly_dash import DjangoDash
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import nd2
import numpy as np
import trackpy as tp
from urllib.parse import parse_qs

# IMPORTS (Passe diese an deine Struktur an)
from Lab_Misc.Load_Data import Load_MFP_Path
from Analysis.models import MFPAnalysis

app = DjangoDash('MFP_AI_Scout')

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
    
    html.H4("KI Scout Tuner (Fluoreszenz / Trackpy)"),
    
    html.Div([
        # ZEILE 1: Bildauswahl
        html.Div([
            html.Div([
                html.Label("1. Scout-Kanal (Detect):"),
                dcc.RadioItems(id='channel-select', options=[], value=None, labelStyle={'marginRight': '15px', 'display': 'inline-block', 'fontWeight': 'bold'})
            ], style={'width': '35%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("2. Frame wählen:"),
                dcc.Slider(id='frame-slider', min=0, max=100, step=1, value=0, tooltip={"placement": "bottom", "always_visible": True}),
            ], style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingLeft': '10px'}),
        ], style={'padding': '15px', 'borderBottom': '1px solid #ccc'}),

        # ZEILE 2: KI-Vorbereitungs-Parameter
        html.Div([
            html.Div([
                html.Label("Expected Diameter (px):", style={'fontWeight': 'bold'}),
                dcc.Input(id='diameter-input', type='number', value=99, min=3, step=2, style={'width': '100%'}),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%', 'verticalAlign': 'top'}),
            
            html.Div([
                html.Label("MinMass (Helligkeits-Schwelle):", style={'fontWeight': 'bold', 'color': '#d9534f'}),
                dcc.Input(id='minmass-input', type='number', value=100000, step=1000, min=0, style={'width': '100%'}),
            ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        ], style={'padding': '15px'}),
        
        # ZEILE 3: Buttons
        html.Div([
            html.Button("🔍 Scout-Vorschau aktualisieren", id='preview-btn', n_clicks=0, className="btn btn-info"),
            html.Button("💾 Setup für KI speichern", id='save-btn', n_clicks=0, className="btn btn-success", style={'float': 'right'}),
        ], style={'padding': '10px'}),
        
    ], style={'backgroundColor': '#eef2f5', 'padding': '5px', 'borderRadius': '5px', 'border': '1px solid #cdd4d9'}),

    # OUTPUT GRAFIK
    dcc.Loading(children=[dcc.Graph(id='preview-image', style={'height': '750px'})], type="circle"),
    html.Br(),
    # STATUS OUTPUT FÜR SPEICHERN
    html.Div(id='status-output', style={'marginTop': '10px', 'fontWeight': 'bold', 'fontSize': '1.2em'})
])

# =========================================================
# CALLBACKS
# =========================================================

@app.callback(
    [Output('frame-slider', 'max'), Output('frame-slider', 'marks'), 
     Output('entry-id', 'data'), 
     Output('diameter-input', 'value'), Output('minmass-input', 'value'),
     Output('channel-select', 'options'), Output('channel-select', 'value')],
    [Input('url', 'search')], [State('entry-id', 'data')]
)
def init_app(search, current_id):
    entry_id = None
    if search:
        try: entry_id = parse_qs(search.lstrip('?'))['id'][0]
        except: pass
    if not entry_id: entry_id = current_id
    def_ret = (10, {}, entry_id, 99, 100000, [], None)
    if not entry_id: return def_ret

    try:
        analysis, _ = MFPAnalysis.objects.get_or_create(Entry_id=entry_id)
        # Wir nutzen die bestehenden DB-Felder
        dia = getattr(analysis, 'Particle_Diameter', 99)
        minmass = getattr(analysis, 'Threshold', 100000) 
        saved_chan = getattr(analysis, 'Detect_Channel', 0)

        path = Load_MFP_Path(entry_id)
        if not path: return def_ret
        
        with nd2.ND2File(path) as f: 
            max_f = f.shape[0]-1
            sizes = {k.lower(): v for k, v in f.sizes.items()}
            if 'c' in sizes:
                count = sizes['c']
                channel_opts = [{'label': f'Channel {i}', 'value': i} for i in range(count)]
                final_chan = saved_chan if saved_chan < count else 0
            else:
                channel_opts = [{'label': 'Mono', 'value': 0}]
                final_chan = 0
        
        return max_f, {0: 'Start', max_f: 'End'}, entry_id, dia, minmass, channel_opts, final_chan
    except: return def_ret

@app.callback(
    Output('preview-image', 'figure'),
    [Input('preview-btn', 'n_clicks'), Input('channel-select', 'value')],
    [State('entry-id', 'data'), State('frame-slider', 'value'), 
     State('diameter-input', 'value'), State('minmass-input', 'value')]
)
def update_graph(n_clicks, ch, entry_id, frame, dia, minmass):
    if not entry_id or ch is None: return go.Figure()

    try:
        path = Load_MFP_Path(entry_id)
        if not path: return go.Figure(layout=dict(title="Pfad Fehler"))
            
        with nd2.ND2File(path) as f:
            img = load_img_data(f, frame, ch)
            if img is None: return go.Figure(layout=dict(title="Fehler beim Laden des Bildes"))
            
            # --- TRACKPY SCOUT LOGIK ---
            # Trackpy verlangt einen ungeraden Diameter
            if dia % 2 == 0: dia += 1
                
            features = tp.locate(img, diameter=dia, minmass=minmass)
            
            # Plotten
            fig = px.imshow(img, color_continuous_scale='gray', origin='upper')
            
            if not features.empty:
                fig.add_trace(go.Scatter(
                    x=features['x'], y=features['y'], 
                    mode='markers', 
                    marker=dict(color='red', symbol='x', size=10, line=dict(width=2)), 
                    name='Scout Seed'
                ))

            fig.update_layout(title=f"Scout Ergebnis | {len(features)} leuchtende Punkte gefunden", height=750)
            return fig
            
    except Exception as e: return go.Figure(layout=dict(title=f"Error: {e}"))

@app.callback(
    Output('status-output', 'children'),
    [Input('save-btn', 'n_clicks')],
    [State('diameter-input', 'value'), State('minmass-input', 'value'), 
     State('channel-select', 'value'), State('entry-id', 'data')]
)
def save_scout_params(n_clicks, dia, minmass, ch, entry_id):
    if n_clicks == 0 or not entry_id: return ""
    
    try:
        analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
        if dia % 2 == 0: dia += 1
        
        # Speichern der Scout-Parameter in der Datenbank
        analysis.Particle_Diameter = dia
        analysis.Threshold = float(minmass) # Wir überschreiben das Threshold-Feld für MinMass
        if hasattr(analysis, 'Detect_Channel'): analysis.Detect_Channel = int(ch)
        analysis.save()
        
        return html.Div([
            html.Span("✅ Scout-Parameter (Diameter & MinMass) erfolgreich für die KI gespeichert!", style={'color':'green'})
        ])
    except Exception as e:
        return html.Div(f"Speicherfehler: {str(e)}", style={'color': 'red'})
    
    # Am Ende der Datei
if __name__ == '__main__':
    app.run_server(debug=True)