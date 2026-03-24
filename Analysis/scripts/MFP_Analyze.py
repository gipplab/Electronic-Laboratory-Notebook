import os
import sys
import concurrent.futures
import multiprocessing

# --- 1. DJANGO INITIALISIERUNG GANZ OBEN ---
# Wir setzen die Umgebungsvariable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings')

import django
from django.apps import apps # WICHTIG: Wir müssen 'apps' explizit importieren!

# Jetzt können wir gefahrlos fragen, ob Django schon wach ist
if not apps.ready:
    django.setup()
# -------------------------------------------

import pandas as pd
import numpy as np
from tqdm import tqdm
import trackpy as tp
import pickle

# --- 2. DEINE NORMALEN IMPORTE ---
from Lab_Misc.Load_Data import Load_MFP_Video

from Analysis.scripts.MFP_Tracking_Logic import process_single_frame, find_edge_dynamic_roi

# =========================================================
# HELPER / MODULE
# =========================================================

def measure_intensity_robust_fast(image, x, y, radius):
    """Berechnet die mittlere Intensität innerhalb eines Radius (High-Speed mit Bounding Box)."""
    if radius < 0.5 or np.isnan(radius): 
        return np.nan
        
    h, w = image.shape
    r_int = int(np.ceil(radius))
    x_int, y_int = int(x), int(y)
    
    # 1. Bounding Box (winziges Fenster) berechnen
    x_min, x_max = max(0, x_int - r_int), min(w, x_int + r_int + 1)
    y_min, y_max = max(0, y_int - r_int), min(h, y_int + r_int + 1)
    
    # 2. Nur diesen winzigen Ausschnitt laden!
    roi = image[y_min:y_max, x_min:x_max]
    
    if roi.size == 0: 
        return np.nan
    
    # 3. Den Kreis NUR in diesem kleinen Fenster berechnen
    Y, X = np.ogrid[:roi.shape[0], :roi.shape[1]]
    loc_x, loc_y = x - x_min, y - y_min
    mask = (X - loc_x)**2 + (Y - loc_y)**2 <= radius**2
    
    return np.mean(roi[mask])

# --- HILFSFUNKTION FÜR DIE ARBEITER (WORKER) ---
# Diese Funktion läuft parallel auf verschiedenen Kernen.
# Sie bekommt ein "Paket" (args) mit allen Infos für EIN Frame.
def _process_single_frame_worker(args):
    # 1. DJANGO INITIALISIEREN (Das ist der Lebensretter für Multiprocessing!)
    import os
    import django
    # Tausche "Private.settings" aus, falls dein Projektordner anders heißt
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings') 
    django.setup()

    # 2. Argumente auspacken
    f_idx, frame_img, diameter, threshold, min_dist, noise_size = args
    
    # 3. Import MUSS hier drinnen bleiben (nach django.setup!)
    from Analysis.scripts.MFP_Tracking_Logic import process_single_frame
    
    # 4. Die eigentliche Arbeit
    _, df, _ = process_single_frame(
        frame_img, 
        diameter=diameter, 
        threshold=threshold, 
        min_dist=min_dist, 
        noise_size=noise_size
    )
    
    if not df.empty:
        df['frame'] = f_idx
        
    return df

# --- DAS NEUE PARALLELE MODUL 1 ---
def perform_tracking_parallel(vid_detect, diameter, threshold, min_dist, noise_size):
    num_cores = multiprocessing.cpu_count()
    print(f"🚀 Starte paralleles Tracking auf {num_cores} CPU-Kernen...")
    
    # 1. Arbeitspakete schnüren (Für jedes Frame im Video ein Paket)
    # Wir übergeben den Index und das exakte Bild
    tasks = [
        (i, vid_detect[i], diameter, threshold, min_dist, noise_size) 
        for i in range(len(vid_detect))
    ]
    
    all_features = []
    
    # 2. Die CPU-Kerne zünden!
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        # map() wirft alle Pakete in den Pool und verteilt sie auf freie Kerne.
        # list() sammelt die Ergebnisse in der richtigen Reihenfolge wieder ein.
        results = list(tqdm(executor.map(_process_single_frame_worker, tasks), total=len(tasks), desc="Tracking (Parallel)"))
        
    # 3. Ergebnisse zusammenbauen
    for df in results:
        if not df.empty:
            all_features.append(df)
            
    if not all_features:
        return pd.DataFrame() # Leer zurückgeben, falls nichts gefunden wurde
        
    return pd.concat(all_features, ignore_index=True)


def perform_linking(features, debug_mode):
    """Modul 2: Verknüpft die Partikel über die Frames hinweg zu Pfaden."""
    print(f"\nLinking {len(features)} Features...")
    
    if debug_mode == 0:
        # Erlaubt dem Partikel, sich bis zu 50 Pixel pro Frame zu bewegen
        # memory=3 bedeutet: Es darf auch mal für 3 Frames dunkel sein, ohne dass die Spur reißt
        tracks = tp.link(features, search_range=50, memory=3)
        
        # Behalte alle Partikel, die in mindestens 2 oder 3 Bildern existieren (statt 5)
        tracks = tp.filter_stubs(tracks, threshold=3)
    else:
        print("⚠️ DEBUG-MODUS: Überspringe Tracking-Links (nur 1 Frame vorhanden).")
        features['particle'] = np.arange(len(features))
        tracks = features
    
    # Qualitäts-Statistik ausgeben
    if 'valid_fit' in tracks.columns and len(tracks) > 0:
        ratio = (tracks['valid_fit'].sum() / len(tracks)) * 100
        print(f"Qualität: {ratio:.1f}% valid radii")
        
    return tracks


# Die Parameter-Liste anpassen (vid_detect hinzufügen!)
def perform_measurements(tracks, vid_measure, vid_detect, diameter):
    """Modul 3: Misst Intensitäten und findet den dynamischen Rand im Brightfield."""
    print("Messe Intensitäten und dynamische Brightfield-Radien...")
    
    # Sicherheits-Check, falls die Tabelle leer ist
    if tracks is None or tracks.empty:
        return pd.DataFrame()
        
    results = []
    
    for row in tqdm(tracks.itertuples(), total=len(tracks), desc="Measuring", unit="spot"):
        # PUNKT-NOTATION STATT KLAMMERN
        frame_idx = int(row.frame)
        curr_bf_img = vid_measure[frame_idx]
        curr_fluo_img = vid_detect[frame_idx] 
        
        # Intensität messen (Punkte statt Klammern!)
        r_mask = row.real_size * 0.5
        intensity = measure_intensity_robust_fast(curr_bf_img, row.x, row.y, r_mask)
        
        # Brightfield Kante finden
        start_radius = row.real_size
        
        # Bei Tuples nimmt man getattr() statt .get()
        valid = getattr(row, 'valid_fit', True) 
        if not valid or start_radius < (diameter * 0.2):
            start_radius = diameter / 2.0

        # Unsere neue V2 Logik
        r_bf, bf_valid = find_edge_dynamic_roi(curr_bf_img, curr_fluo_img, row.x, row.y, start_radius)
        
        results.append({
            'intensity_measure': intensity,
            'radius_brightfield': r_bf,
            'radius_brightfield_valid': bf_valid
        })

    # Ergebnisse zusammenführen
    res_df = pd.DataFrame(results)
    return pd.concat([tracks.reset_index(drop=True), res_df], axis=1)

# VERGISS NICHT: Wenn du die Funktion unten im "Koordinator" aufrufst, 
# musst du `vid_detect` jetzt mit übergeben:
# final_tracks = perform_measurements(tracks, vid_measure, vid_detect, DIAMETER)


# =========================================================
# HAUPT-PIPELINE (Der Koordinator)
# =========================================================

def run_full_analysis(analysis_obj):
    DEBUG_MODE = 0
    
    entry_id = analysis_obj.Entry_id
    print(f"--- STARTE FULL ANALYSE (ID: {entry_id}) ---")

    # 1. Daten laden
    video_data = Load_MFP_Video(entry_id)
    if not video_data:
        return False, f"Fehler beim Laden der Daten für ID {entry_id}"
    
    vid_detect = video_data['detect']
    vid_measure = video_data['measure']
    file_path = video_data['path']
    print(f"File geladen: {file_path}")
    
    # 2. Parameter extrahieren
    DIAMETER = analysis_obj.Particle_Diameter
    THRESHOLD = analysis_obj.Threshold
    MIN_DIST = getattr(analysis_obj, 'Min_Dist', 70)
    NOISE_SIZE = getattr(analysis_obj, 'Noise_Size', 3.0)

    # 3. Debug Modus anwenden
    if DEBUG_MODE == 1:
        print("⚠️ DEBUG-MODUS AKTIV: Verarbeite nur den ersten Frame!")
        vid_detect = vid_detect[:1]
        vid_measure = vid_measure[:1]

    # --- DIE MODULARE PIPELINE ---
    
    # Schritt A: Tracking (JETZT PARALLEL!)
    features = perform_tracking_parallel(vid_detect, DIAMETER, THRESHOLD, MIN_DIST, NOISE_SIZE)
    if features.empty:
        return False, "Keine Partikel gefunden."

    # Schritt B: Linking
    tracks = perform_linking(features, DEBUG_MODE)
    if tracks.empty:
        return False, "Nach dem Linking blieben keine Partikel übrig."

    # Schritt C: Messen (Brightfield Kanten & Intensität)
    # Schritt C: Messen (Brightfield Kanten & Intensität)
    final_tracks = perform_measurements(tracks, vid_measure, vid_detect, DIAMETER)

    # -----------------------------

    # 4. Speichern
    analysis_dir = os.path.join(os.path.dirname(file_path), "Analysis")
    os.makedirs(analysis_dir, exist_ok=True)
        
    output_pkl = os.path.join(analysis_dir, "tracking_data.pkl")
    output_csv = os.path.join(analysis_dir, "tracking_data.csv")
    
    export_data = {
        'tracks': final_tracks, 
        'source_file': file_path,
        'parameters': {
            'diameter': DIAMETER, 'threshold': THRESHOLD, 
            'min_dist': MIN_DIST, 'noise_size': NOISE_SIZE
        }
    }
    
    with open(output_pkl, 'wb') as f:
        pickle.dump(export_data, f)

    final_tracks.to_csv(output_csv, index=False)
    print(f"💾 Daten gespeichert in: {analysis_dir}")

    # Datenbank Update
    analysis_obj.Result_Path = output_pkl
    analysis_obj.save()
    
    return True, f"Erfolg! {final_tracks['particle'].nunique()} Spuren."

run_analysis = run_full_analysis