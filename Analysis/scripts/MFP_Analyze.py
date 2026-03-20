import os
import pickle
import numpy as np
import pandas as pd
import trackpy as tp
from tqdm import tqdm

from Lab_Misc.General import get_BasePath
from Lab_Misc.Load_Data import Load_MFP_Path, Load_MFP_Video
from Analysis.scripts.MFP_Tracking_Logic import process_single_frame, find_edge_dynamic_roi

# =========================================================
# HELPER / MODULE
# =========================================================

def measure_intensity_robust(image, x, y, radius):
    """Berechnet die mittlere Intensität innerhalb eines Radius."""
    if radius < 0.5: return np.nan
    h, w = image.shape
    if x < radius or x > w - radius or y < radius or y > h - radius:
        return np.nan
    
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - x)**2 + (Y - y)**2)
    mask = dist_from_center <= radius
    return np.mean(image[mask])


def perform_tracking(vid_detect, diameter, threshold, min_dist, noise_size):
    """Modul 1: Findet die Positionen und optimiert die Mitte in jedem Frame."""
    all_frames_features = []
    print(f"Starte Tracking auf {len(vid_detect)} Frames...")
    
    for t, frame in enumerate(tqdm(vid_detect, desc="Tracking", unit="frame")):
        _, df_final, _ = process_single_frame(
            frame, 
            diameter=diameter, 
            threshold=threshold, 
            min_dist=min_dist, 
            noise_size=noise_size
        )
        if not df_final.empty:
            df_final['frame'] = t
            all_frames_features.append(df_final)

    if not all_frames_features:
        return pd.DataFrame()
        
    return pd.concat(all_frames_features, ignore_index=True)


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
    results = []
    
    for idx, row in tqdm(tracks.iterrows(), total=len(tracks), desc="Measuring", unit="spot"):
        frame_idx = int(row['frame'])
        curr_bf_img = vid_measure[frame_idx]
        curr_fluo_img = vid_detect[frame_idx] 
        
        # Intensität messen
        r_mask = row['real_size'] * 0.5
        intensity = measure_intensity_robust(curr_bf_img, row['x'], row['y'], r_mask)
        
        # Brightfield Kante finden
        start_radius = row['real_size']
        if not row.get('valid_fit', True) or start_radius < (diameter * 0.2):
            start_radius = diameter / 2.0

        # Unsere neue V2 Logik
        r_bf, bf_valid = find_edge_dynamic_roi(curr_bf_img, curr_fluo_img, row['x'], row['y'], start_radius)
        
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
    
    # Schritt A: Tracking
    features = perform_tracking(vid_detect, DIAMETER, THRESHOLD, MIN_DIST, NOISE_SIZE)
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