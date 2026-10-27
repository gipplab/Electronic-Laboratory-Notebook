"""Interactive Yeast-FLIM results view (reference image with Cellpose masks, per-cell time courses).

Pattern follows the MFP dashboards: a DjangoDash app embedded via ``plotly_app`` and
initialised with ``{'entry-id': {'data': pk}}``. It only reads existing YFL artifacts.
"""

import base64
import io
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output, State
from django_plotly_dash import DjangoDash
from plotly.subplots import make_subplots
from scipy import ndimage as ndi

from Analysis.scripts.Yeast_FLIM_Results import (
    INTENSITY_CSV,
    MANIFEST_JSON,
    MASK_TIFF,
    OVERLAY_PNG,
    QC_CSV,
    inspect_results,
)
from Exp_Main.models import YFL

app = DjangoDash('YFL_Dashboard')

PALETTE = pc.qualitative.Dark24
ALERT_STYLE = {
    'danger': {'background': '#f8d7da', 'color': '#842029', 'border': '1px solid #f5c2c7'},
    'warning': {'background': '#fff3cd', 'color': '#664d03', 'border': '1px solid #ffecb5'},
    'info': {'background': '#cff4fc', 'color': '#055160', 'border': '1px solid #b6effb'},
}
METRICS = [
    ('area_px', 'Zellfläche (px²)'),
    ('mean_raw_pixel_value', 'Mittlere Roh-Intensität (a.u.)'),
    ('integrated_raw_pixel_value', 'Integrierte Roh-Intensität (a.u.)'),
    ('mean_background_corrected', 'Mittlere Intensität, hintergrundkorr. (a.u.)'),
    ('integrated_background_corrected', 'Integrierte Intensität, hintergrundkorr. (a.u.)'),
]


def _alert(level, text):
    return html.Div(text, style={**ALERT_STYLE[level], 'padding': '8px 12px', 'margin': '6px 0', 'borderRadius': '4px'})


def _card(title, value, sub=None):
    children = [html.Div(title, style={'fontSize': '0.8em', 'color': '#6c757d'}),
                html.Div(value, style={'fontSize': '1.4em', 'fontWeight': 'bold'})]
    if sub:
        children.append(html.Div(sub, style={'fontSize': '0.75em', 'color': '#6c757d'}))
    return html.Div(children, style={'border': '1px solid #dee2e6', 'borderRadius': '6px',
                                     'padding': '8px 14px', 'minWidth': '150px', 'background': '#fff'})


def _entry(pk):
    try:
        return YFL.objects.get(pk=int(pk))
    except (TypeError, ValueError, YFL.DoesNotExist):
        return None


@lru_cache(maxsize=8)
def _read_csv(path, mtime_ns, size):
    return pd.read_csv(path)


def _csv(path):
    path = Path(path)
    if not path.is_file():
        return None
    stat = path.stat()
    try:
        return _read_csv(str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError, pd.errors.ParserError):
        return None


def _data_uri(image):
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


@lru_cache(maxsize=4)
def _reference_plane(path, mtime_ns, seg_time, seg_channel, seg_z):
    import tifffile

    with tifffile.TiffFile(path) as tif:
        series = tif.series[0]
        data, axes = series.asarray(), series.axes.upper()
    index, remaining = [], []
    selected = {'T': seg_time, 'C': seg_channel, 'Z': seg_z}
    for axis, size in zip(axes, data.shape):
        if axis in 'YX':
            index.append(slice(None))
            remaining.append(axis)
        elif axis in selected:
            index.append(selected[axis])
        elif size == 1:
            index.append(0)
        else:
            raise ValueError(f'Unselected axis {axis} in reference image.')
    plane = np.asarray(data[tuple(index)])
    return plane.T if remaining == ['X', 'Y'] else plane


@lru_cache(maxsize=4)
def _masks(path, mtime_ns):
    import tifffile

    return np.asarray(tifffile.imread(path))


def _display_gray(plane):
    low, high = np.percentile(plane, (1, 99.5))
    gray = np.clip((plane.astype(np.float32) - low) / max(float(high - low), 1e-8), 0, 1)
    return np.repeat((gray * 255).astype(np.uint8)[..., None], 3, axis=2)


def _mask_overlay(masks, selected):
    """RGBA fill of all Cellpose masks; selected cells are emphasised with an outline."""
    rgba = np.zeros(masks.shape + (4,), dtype=np.uint8)
    colors = np.array([[int(c) for c in pc.hex_to_rgb(PALETTE[i % len(PALETTE)])]
                       for i in range(int(masks.max()) + 1)], dtype=np.uint8)
    inside = masks > 0
    rgba[inside, :3] = colors[masks[inside]]
    rgba[inside, 3] = 45 if selected else 95
    if selected:
        chosen = np.isin(masks, list(selected))
        rgba[chosen, 3] = 130
        outline = chosen & ~ndi.binary_erosion(chosen)
        rgba[outline] = (255, 255, 255, 255)
    return rgba


def _manifest_params(manifest):
    return (manifest or {}).get('parameters') or {}


def _load(pk):
    entry = _entry(pk)
    if entry is None:
        return None, None, None, None
    info = inspect_results(entry)
    intensity = _csv(info['files'][INTENSITY_CSV]) if info['present'][INTENSITY_CSV] else None
    qc = _csv(info['files'][QC_CSV]) if info['present'][QC_CSV] else None
    return entry, info, intensity, qc


def _elapsed_hours(manifest, timepoints):
    axis = ((manifest or {}).get('time_axis') or {}).get('frame_elapsed_s')
    if isinstance(axis, list) and len(axis) == (manifest.get('completeness') or {}).get('signal_timepoints'):
        return {t: axis[t] / 3600.0 for t in timepoints if 0 <= t < len(axis)}
    return None


def _lifetime_panel(manifest):
    inventory = (((manifest or {}).get('lifetime_phasor') or {}).get('leica_flim_products_in_lif')) or {}
    facts = []
    if inventory.get('has_fast_flim_map') or inventory.get('has_phasor_real_imaginary_maps'):
        facts.append(
            'Die LIF enthält neben der Intensität von LAS X berechnete 16-bit-Karten (Fast FLIM, '
            'Phasor Real/Imaginär). Ihre Kodierung/Skalierung und eine gemessene Phasor-Kalibrierung '
            'werden hier nicht verifiziert; sie werden daher nicht importiert oder dargestellt.')
    if inventory.get('phasor_automatic_reference'):
        facts.append('Die Phasor-Referenz in den Leica-Metadaten ist „automatisch“ – eine gemessene '
                     'Kalibrierung an einem Standard bekannter Lebensdauer ist nicht dokumentiert.')
    if inventory.get('has_global_decay_histogram_in_xml'):
        facts.append('Im LIF-XML liegt nur ein globales (bildweites) Abklinghistogramm vor, '
                     'keine pixel- oder zellaufgelösten Photon-Ankunftszeiten.')
    if inventory.get('laser_pulse_frequency_hz'):
        facts.append(f"Gespeicherte Laserpulsfrequenz: {inventory['laser_pulse_frequency_hz'] / 1e6:.2f} MHz.")
    return html.Div([
        html.H4('Fluoreszenzlebensdauer / klassischer FLIM-Phasor'),
        _alert('info', 'Nicht in dieser LIF-Serie enthalten. Die analysierte Serie „FLIM Compressed/Intensity“ '
                       'enthält nur rohe Intensitätswerte; daraus werden weder Lebensdauern noch Phasorwerte '
                       'berechnet. Daher gibt es hier bewusst keinen Lifetime- oder Phasor-Plot.'),
        html.Div('Für eine echte Auswertung fehlen: pixel- bzw. zellaufgelöste, angepasste Lebensdauern oder '
                 'Photon-Ankunftszeit-Histogramme (Leica-FALCON-Rohdaten/Export) sowie Laserpulsfrequenz, '
                 'Instrumentenantwort und eine Phasor-Kalibrierung mit gemessener Referenz bekannter Lebensdauer. '
                 'Ein spektraler Phasor (Emissionsspektrum) ist eine andere Methode und kein Ersatz für den '
                 'klassischen FLIM-Phasor.'),
        html.Ul([html.Li(f) for f in facts]) if facts else None,
    ], style={'marginTop': '24px'})


app.layout = html.Div([
    dcc.Store(id='entry-id'),
    html.Div(id='yfl-notices'),
    html.H4('Kennzahlen'),
    html.Div(id='yfl-kpis', style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '10px', 'marginBottom': '8px'}),
    html.Div(id='yfl-downloads', style={'marginBottom': '16px'}),

    html.H4('Referenzbild mit Cellpose-Masken'),
    html.Div([
        dcc.RadioItems(
            id='image-mode', value='overlay', inline=True,
            options=[{'label': ' Original', 'value': 'original'},
                     {'label': ' Overlay (Cellpose-Masken, transparent)', 'value': 'overlay'},
                     {'label': ' Gespeichertes Konturbild (PNG)', 'value': 'png'}],
            labelStyle={'marginRight': '16px'}),
    ]),
    html.Div(id='image-caption', style={'fontSize': '0.85em', 'color': '#495057', 'margin': '4px 0'}),
    dcc.Graph(id='image-graph', style={'height': '70vh'}, config={'responsive': True}),

    html.H4('Zeitverläufe pro Zelle'),
    html.Div([
        html.Div([
            html.Label('Zellen hervorheben (Klick auf Zelle im Bild oder Auswahl):', style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='cell-select', options=[], value=[], multi=True, placeholder='Alle Zellen grau, Median schwarz'),
        ], style={'flex': '1 1 420px'}),
        html.Div([
            html.Label('Zeitachse:', style={'fontWeight': 'bold'}),
            dcc.RadioItems(id='xaxis-mode', value='index', inline=True,
                           options=[{'label': ' Zeitindex', 'value': 'index'}],
                           labelStyle={'marginRight': '12px'}),
        ], style={'flex': '0 0 auto', 'marginLeft': '24px'}),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'alignItems': 'flex-end'}),
    html.Div(id='ts-note', style={'fontSize': '0.85em', 'color': '#495057', 'margin': '4px 0'}),
    dcc.Graph(id='timeseries-graph', style={'height': '1100px'}),
    html.Div(id='lifetime-panel'),
], style={'padding': '8px'})


@app.callback(
    [Output('yfl-notices', 'children'), Output('yfl-kpis', 'children'),
     Output('yfl-downloads', 'children'), Output('cell-select', 'options'),
     Output('xaxis-mode', 'options'), Output('lifetime-panel', 'children')],
    [Input('entry-id', 'data')],
)
def init_view(pk):
    entry, info, intensity, qc = _load(pk)
    if entry is None:
        return [_alert('danger', 'Experiment nicht gefunden.')], [], [], [], [{'label': ' Zeitindex', 'value': 'index'}], None
    manifest = info['manifest']
    notices = [_alert(level, text) for level, text in info['messages']]
    if info['state'] == 'partial':
        notices.append(_alert('warning', 'Dargestellt werden nur die vorhandenen Dateien; Werte können unvollständig sein.'))
    kpis = []
    if intensity is not None and len(intensity):
        completeness = (manifest or {}).get('completeness') or {}
        n_t = int(intensity['time_index'].nunique())
        expected_t = completeness.get('signal_timepoints')
        areas = intensity.drop_duplicates('cell_id')['area_px']
        first, last = intensity['time_index'].min(), intensity['time_index'].max()
        med_first = intensity.loc[intensity['time_index'] == first, 'mean_raw_pixel_value'].median()
        med_last = intensity.loc[intensity['time_index'] == last, 'mean_raw_pixel_value'].median()
        no_bg = int(intensity.loc[intensity['background_pixel_count'] == 0, 'cell_id'].nunique())
        kpis += [
            _card('Zellen', f"{intensity['cell_id'].nunique()}"),
            _card('Zeitpunkte', f"{n_t}" + (f' / {expected_t}' if expected_t else ''),
                  'vollständig' if expected_t == n_t else 'unvollständig oder unbekannt'),
            _card('Zellfläche (Median)', f'{areas.median():.0f} px²', f'{areas.min()} – {areas.max()} px² (feste Maske)'),
            _card(f'Median mittlere Roh-Int. t={first}', f'{med_first:.4g}'),
            _card(f'Median mittlere Roh-Int. t={last}', f'{med_last:.4g}'),
            _card('Zellen ohne Hintergrund-Pixel', str(no_bg), 'Hintergrundkorrektur dort nicht definiert' if no_bg else None),
        ]
    if qc is not None and len(qc):
        border = int(qc['touches_image_border'].astype(str).str.lower().eq('true').sum())
        kpis.append(_card('Zellen am Bildrand', str(border), f'von {len(qc)} Masken'))
    params = _manifest_params(manifest)
    if manifest:
        kpis.append(_card('Cellpose-Modell', str(manifest.get('cellpose_model', '–')),
                          f"Referenz t={params.get('segmentation_time_index', '–')}, Ring {params.get('background_ring_width_px', '–')} px"))
    links = []
    for name, label in [(INTENSITY_CSV, 'Intensitäten (CSV)'), (QC_CSV, 'Masken-QC (CSV)'),
                        (MANIFEST_JSON, 'Manifest (JSON)'), (OVERLAY_PNG, 'Overlay (PNG)'), (MASK_TIFF, 'Masken (OME-TIFF)')]:
        if info['present'][name]:
            links.append(html.A(label, href=f"/Analysis/Yeast_FLIM/{entry.pk}/download/{name}/",
                                className='btn btn-sm btn-outline-primary', style={'marginRight': '6px'}))
    downloads = [html.Span('Download: ', style={'fontWeight': 'bold'})] + links if links else []

    options = []
    if intensity is not None:
        areas = intensity.drop_duplicates('cell_id').set_index('cell_id')['area_px']
        options = [{'label': f'Zelle {cid} ({int(areas[cid])} px²)', 'value': int(cid)} for cid in sorted(areas.index)]
    axis_options = [{'label': ' Zeitindex', 'value': 'index'}]
    if intensity is not None and _elapsed_hours(manifest, intensity['time_index'].unique()) is not None:
        axis_options.append({'label': ' Reale Zeit (h seit erstem Frame, LIF-Zeitstempel)', 'value': 'real'})
    return notices, kpis, downloads, options, axis_options, _lifetime_panel(manifest)


@app.callback(
    [Output('image-graph', 'figure'), Output('image-caption', 'children')],
    [Input('entry-id', 'data'), Input('image-mode', 'value'), Input('cell-select', 'value')],
)
def update_image(pk, mode, selected):
    fig = go.Figure()
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), uirevision='yfl-image')
    entry, info, intensity, qc = _load(pk)
    if entry is None:
        return fig, 'Experiment nicht gefunden.'
    selected = {int(c) for c in (selected or [])}
    manifest = info['manifest']
    params = _manifest_params(manifest)
    ref_path = ((manifest or {}).get('inputs') or {}).get('segmentation', {}).get('path')
    mask_file = info['files'][MASK_TIFF]
    overlay_file = info['files'][OVERLAY_PNG]

    images, caption, shape = [], '', None
    try:
        if mode == 'png':
            if not info['present'][OVERLAY_PNG]:
                return fig, 'yeast_segmentation_overlay.png fehlt.'
            from PIL import Image
            with Image.open(overlay_file) as img:
                shape = (img.height, img.width)
                uri = _data_uri(np.asarray(img.convert('RGB')))
            images.append(dict(source=uri, layer='below'))
            caption = ('Gespeichertes Konturbild der Segmentierung (rote Konturen sind in das Bild '
                       'eingebrannt, Anzeige-Kontrast 1–99,5 %-Perzentil); keine Messdaten.')
        else:
            if not ref_path or not Path(ref_path).is_file():
                return fig, 'Referenzbild (OME-TIFF aus dem LIF-Import) nicht gefunden; nur das gespeicherte Konturbild kann gezeigt werden.'
            plane = _reference_plane(ref_path, Path(ref_path).stat().st_mtime_ns,
                                     int(params.get('segmentation_time_index', 0)),
                                     int(params.get('segmentation_channel_index', 0)),
                                     int(params.get('segmentation_z_index', 0)))
            shape = plane.shape
            images.append(dict(source=_data_uri(_display_gray(plane)), layer='below'))
            caption = (f"Original: Referenzbild t={params.get('segmentation_time_index', '–')} "
                       '(Anzeige-Kontrast 1–99,5 %-Perzentil, nur Darstellung).')
            if mode == 'overlay':
                if not info['present'][MASK_TIFF]:
                    caption += ' Maskendatei fehlt – kein Overlay möglich.'
                else:
                    masks = _masks(str(mask_file), mask_file.stat().st_mtime_ns)
                    if masks.shape != shape:
                        caption += ' Masken- und Bildgröße stimmen nicht überein – Overlay nicht angezeigt.'
                    else:
                        images.append(dict(source=_data_uri(_mask_overlay(masks, selected)), layer='above'))
                        caption = (f"Overlay: Cellpose-Masken ({manifest.get('cellpose_model', '?')}, "
                                   f"{int(masks.max())} Zellen) transparent über Referenzbild t={params.get('segmentation_time_index', '–')}. "
                                   'Masken wurden nur auf diesem Referenzbild berechnet und sind für alle Zeitpunkte fest.')
    except Exception as exc:
        return fig, f'Bild konnte nicht geladen werden: {exc}'

    height, width = shape
    for image in images:
        fig.add_layout_image(dict(**image, xref='x', yref='y', x=0, y=0, sizex=width, sizey=height,
                                  xanchor='left', yanchor='top', sizing='stretch', opacity=1))
    if qc is not None and len(qc):
        fig.add_trace(go.Scatter(
            x=qc['centroid_x_px'] + 0.5, y=qc['centroid_y_px'] + 0.5, mode='markers',
            marker=dict(size=9, color='rgba(255,255,255,0.01)'), customdata=qc['cell_id'],
            text=[f'{a} px²' for a in qc['area_px']],
            hovertemplate='Zelle %{customdata}<br>Fläche %{text}<extra></extra>', showlegend=False))
    else:
        fig.add_trace(go.Scatter(x=[0, width], y=[0, height], mode='markers', opacity=0, showlegend=False, hoverinfo='skip'))
    fig.update_xaxes(range=[0, width], showgrid=False, zeroline=False, title='x (px)')
    fig.update_yaxes(range=[height, 0], showgrid=False, zeroline=False, scaleanchor='x', title='y (px)')
    return fig, caption


@app.callback(
    Output('cell-select', 'value'),
    [Input('image-graph', 'clickData')],
    [State('cell-select', 'value')],
    prevent_initial_call=True,
)
def toggle_clicked_cell(click, current):
    current = list(current or [])
    try:
        cell = int(click['points'][0]['customdata'])
    except (TypeError, KeyError, IndexError, ValueError):
        return current
    return [c for c in current if c != cell] if cell in current else current + [cell]


@app.callback(
    [Output('timeseries-graph', 'figure'), Output('ts-note', 'children')],
    [Input('entry-id', 'data'), Input('cell-select', 'value'), Input('xaxis-mode', 'value')],
)
def update_timeseries(pk, selected, xmode):
    entry, info, intensity, _ = _load(pk)
    fig = go.Figure()
    if entry is None or intensity is None or intensity.empty:
        fig.update_layout(annotations=[dict(text='Keine Intensitätsdaten vorhanden', showarrow=False)])
        return fig, ''
    manifest = info['manifest']
    selected = [int(c) for c in (selected or [])]
    hours = _elapsed_hours(manifest, intensity['time_index'].unique()) if xmode == 'real' else None
    use_real = hours is not None
    xcol = intensity['time_index'].map(hours) if use_real else intensity['time_index']
    data = intensity.assign(_x=xcol).sort_values(['cell_id', 'time_index'])
    xlabel = 'Zeit seit erstem Frame (h, LIF-Zeitstempel)' if use_real else 'Zeitindex'

    fig = make_subplots(rows=len(METRICS), cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=[label for _, label in METRICS])
    n_cells = data['cell_id'].nunique()
    for row, (col, label) in enumerate(METRICS, start=1):
        pivot = data.pivot(index='time_index', columns='cell_id', values=col)
        xs = data.drop_duplicates('time_index').set_index('time_index')['_x'].reindex(pivot.index)
        # All cells in one grey trace (NaN-separated) keeps hundreds of cells responsive.
        gx, gy, gid = [], [], []
        for cell in pivot.columns:
            gx += list(xs.values) + [np.nan]
            gy += list(pivot[cell].values) + [np.nan]
            gid += [int(cell)] * len(xs) + [None]
        fig.add_trace(go.Scatter(x=gx, y=gy, customdata=gid, mode='lines', line=dict(color='rgba(120,120,120,0.35)', width=1),
                                 name='Einzelzellen', legendgroup='all', showlegend=(row == 1),
                                 hovertemplate='Zelle %{customdata}<br>x=%{x:.3g}<br>y=%{y:.4g}<extra></extra>'), row=row, col=1)
        q1, med, q3 = (pivot.quantile(0.25, axis=1), pivot.median(axis=1), pivot.quantile(0.75, axis=1))
        fig.add_trace(go.Scatter(x=xs, y=q3, mode='lines', line=dict(width=0), hoverinfo='skip', showlegend=False), row=row, col=1)
        fig.add_trace(go.Scatter(x=xs, y=q1, mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0,0,0,0.15)',
                                 name='Interquartilbereich', legendgroup='iqr', showlegend=(row == 1), hoverinfo='skip'), row=row, col=1)
        fig.add_trace(go.Scatter(x=xs, y=med, mode='lines+markers', line=dict(color='black', width=2.5), marker=dict(size=4),
                                 name=f'Median über Zellen (n={n_cells})', legendgroup='median', showlegend=(row == 1)), row=row, col=1)
        for i, cell in enumerate(selected):
            if cell in pivot.columns:
                fig.add_trace(go.Scatter(x=xs, y=pivot[cell], mode='lines+markers', marker=dict(size=4),
                                         line=dict(color=PALETTE[cell % len(PALETTE)], width=2), name=f'Zelle {cell}',
                                         legendgroup=f'cell{cell}', showlegend=(row == 1)), row=row, col=1)
        fig.update_yaxes(title_text=label.split(' (')[0] if row else None, row=row, col=1)
    fig.update_xaxes(title_text=xlabel, row=len(METRICS), col=1)
    fig.update_layout(height=1100, hovermode='closest', uirevision='yfl-ts', margin=dict(l=70, r=20, t=40, b=50),
                      legend=dict(orientation='h', y=1.04))
    note = ('Die Zellfläche ist konstant, weil eine feste Maske aus dem Referenzbild auf alle Zeitpunkte angewendet wird. '
            'Intensitäten sind rohe Float-Pixelwerte der Leica-Intensitätsserie (keine Photonenzahl, keine Lebensdauer); '
            'hintergrundkorrigiert = Roh-Wert minus Median eines lokalen Rings außerhalb aller Masken.')
    if not use_real:
        note += ' Zeitachse: Zeitindex' + (' (LIF-Zeitstempel nicht eindeutig zuordenbar).' if not hours and (manifest or {}).get('time_axis') else '.')
    return fig, note
