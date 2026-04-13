from django_plotly_dash import DjangoDash
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import nd2
import numpy as np
import pandas as pd
from urllib.parse import parse_qs
from scipy.ndimage import gaussian_filter
from skimage.feature import peak_local_max

# IMPORTS
from Lab_Misc.Load_Data import Load_MFP_Path, Load_MFP_Video
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
    
    html.H4("KI Scout Tuner (Peak Local Max)"),
    
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
                dcc.Input(id='diameter-input', type='number', value=51, min=3, step=2, style={'width': '100%'}),
                
                # NEU: Box-Size Eingabe
                html.Label("KI Box-Größe (Ausschnitt in px):", style={'fontWeight': 'bold', 'color': 'purple', 'marginTop': '10px'}),
                dcc.Input(id='box-size-input', type='number', value=100, min=10, step=2, style={'width': '100%'}),
            ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '2%', 'verticalAlign': 'top'}),
            
            html.Div([
                # ANGEPASST: Float-Threshold statt MinMass
                html.Label("Threshold (Helligkeit 0.01 - 0.50):", style={'fontWeight': 'bold', 'color': '#d9534f'}),
                dcc.Input(id='minmass-input', type='number', value=0.05, step=0.01, min=0, style={'width': '100%'}),
                
                # NEU: Analyse Modus
                html.Label("KI Modus:", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                dcc.RadioItems(
                    id='run-mode-select', 
                    options=[{'label': ' Nur diesen Frame rechnen', 'value': 'single'}, 
                             {'label': ' Komplettes Video rechnen', 'value': 'all'}], 
                    value='single', 
                    labelStyle={'display': 'block'}
                )
            ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        ], style={'padding': '15px'}),
        
        # ZEILE 3: Buttons
        html.Div([
            html.Button("🔍 Scout-Vorschau aktualisieren", id='preview-btn', n_clicks=0, className="btn btn-info"),
            html.Button("🧬 Cellpose Analyse starten", id='cellpose-btn', n_clicks=0, className="btn btn-warning", style={'marginLeft': '10px'}),
            html.Button("💾 Setup für KI speichern", id='save-btn', n_clicks=0, className="btn btn-success", style={'float': 'right'}),
        ], style={'padding': '10px'}),
        
    ], style={'backgroundColor': '#eef2f5', 'padding': '5px', 'borderRadius': '5px', 'border': '1px solid #cdd4d9'}),

    # OUTPUT GRAFIK
    dcc.Loading(children=[dcc.Graph(id='preview-image', style={'height': '750px'})], type="circle"),
    html.Br(),
    
    html.Div(id='save-status', style={'marginTop': '10px', 'fontWeight': 'bold', 'fontSize': '1.2em'}),
    
    dcc.Loading(
        children=[html.Div(id='cellpose-status', style={'marginTop': '20px'})], 
        type="default"
    )
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
    def_ret = (10, {}, entry_id, 51, 0.05, [], None)
    if not entry_id: return def_ret

    try:
        analysis, _ = MFPAnalysis.objects.get_or_create(Entry_id=entry_id)
        dia = getattr(analysis, 'Particle_Diameter', 51)
        minmass = getattr(analysis, 'Threshold', 0.05) 
        if minmass >= 1.0: minmass = 0.05 # Korrektur falls alte Trackpy Werte drin stehen
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
     State('diameter-input', 'value'), State('minmass-input', 'value'),
     State('box-size-input', 'value')] # <-- NEU
)
def update_graph(n_clicks, ch, entry_id, frame, dia, minmass, box_size):
    if not entry_id or ch is None: return go.Figure()

    try:
        path = Load_MFP_Path(entry_id)
        if not path: return go.Figure(layout=dict(title="Pfad Fehler"))
            
        with nd2.ND2File(path) as f:
            img = load_img_data(f, frame, ch)
            if img is None: return go.Figure(layout=dict(title="Fehler beim Laden des Bildes"))
            
            # --- DIE NEUE PEAK LOCAL MAX METHODE ---
            img_float = img.astype(float)
            smart_sigma = max(2, int(dia / 5))
            img_blur = gaussian_filter(img_float, sigma=smart_sigma)
            
            min_dist = max(5, int(dia * 0.4))
            
            coordinates = peak_local_max(img_blur, min_distance=min_dist, threshold_rel=float(minmass))
            if len(coordinates) > 0:
                features = pd.DataFrame({'x': coordinates[:, 1], 'y': coordinates[:, 0]})
            else:
                features = pd.DataFrame(columns=['x', 'y'])
            
            fig = px.imshow(img, color_continuous_scale='gray', origin='upper')
            
            if not features.empty:
                # 1. Das rote Scout-Kreuz im Zentrum
                fig.add_trace(go.Scatter(
                    x=features['x'], y=features['y'], mode='markers', 
                    marker=dict(color='red', symbol='x', size=8, line=dict(width=2)), name='Scout Seed'
                ))

                # 2. NEU: Die lila Boxen einzeichnen!
                if box_size:
                    half_b = box_size / 2
                    shapes = []
                    for _, row in features.iterrows():
                        shapes.append(dict(
                            type="rect",
                            x0=row['x'] - half_b, y0=row['y'] - half_b,
                            x1=row['x'] + half_b, y1=row['y'] + half_b,
                            line=dict(color="purple", width=1.5, dash="dot")
                        ))
                    fig.update_layout(shapes=shapes)

            fig.update_layout(title=f"Frame {frame} | Scout Ergebnis: {len(features)} Partikel", height=750)
            return fig
            
    except Exception as e: return go.Figure(layout=dict(title=f"Error: {e}"))

@app.callback(
    Output('save-status', 'children'),
    [Input('save-btn', 'n_clicks')],
    [State('diameter-input', 'value'), State('minmass-input', 'value'), 
     State('channel-select', 'value'), State('entry-id', 'data')]
)
def save_scout_params(n_clicks, dia, minmass, ch, entry_id):
    if n_clicks == 0 or not entry_id: return ""
    try:
        analysis = MFPAnalysis.objects.get(Entry_id=entry_id)
        analysis.Particle_Diameter = dia
        analysis.Threshold = float(minmass)
        if hasattr(analysis, 'Detect_Channel'): analysis.Detect_Channel = int(ch)
        analysis.save()
        return html.Span("✅ Setup erfolgreich gespeichert!", style={'color':'green'})
    except Exception as e: return html.Div(f"Speicherfehler: {str(e)}", style={'color': 'red'})

@app.callback(
    Output('cellpose-status', 'children'),
    [Input('cellpose-btn', 'n_clicks')],
    # NEU: Wir laden box_size, frame und run_mode mit in den Callback
    [State('entry-id', 'data'), State('diameter-input', 'value'), State('minmass-input', 'value'),
     State('box-size-input', 'value'), State('frame-slider', 'value'), State('run-mode-select', 'value')]
)
def cellpose_click(n_clicks, entry_id, dia, minmass, box_size, frame, run_mode):
    if n_clicks == 0 or not entry_id:
        return ""
    
    try:
        from Analysis.scripts.Cellpose_Cement import run_cellpose_cement_analysis
        
        # Startet die Backend-Funktion mit den neuen Parametern
        success, progress_message = run_cellpose_cement_analysis(entry_id, dia, minmass, box_size, frame, run_mode, None)
        
        lines = progress_message.split('\n')
        output = html.Div([
            html.Div(line, style={
                'color': 'green' if '✅' in line else ('red' if '❌' in line else ('orange' if '⚠️' in line else 'black')),
                'marginBottom': '2px', 'fontFamily': 'monospace', 'fontSize': '12px'
            })
            for line in lines if line.strip()
        ], style={'whiteSpace': 'pre-wrap', 'backgroundColor': '#f5f5f5', 'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #ddd', 'maxHeight': '400px', 'overflowY': 'auto'})
        
        return output
            
    except Exception as e:
        import traceback
        return html.Div(f"❌ Fehler: {str(e)}\n\n{traceback.format_exc()}", style={'color': 'red', 'whiteSpace': 'pre-wrap'})

if __name__ == '__main__':
    app.run_server(debug=True)