import nd2
import numpy as np
import trackpy as tp
import pandas as pd
import os
import pickle
from tqdm import tqdm
from Analysis.scripts.MFP_Tracking_Logic import process_single_frame, find_edge_in_channel0
from Lab_Misc.General import get_BasePath

# --- KORREKTE IMPORTS (Ganz oben!) ---
from Lab_Misc.Load_Data import Load_MFP_Path 
from Analysis.scripts.MFP_Tracking_Logic import process_single_frame

# =========================================================
# HELPER
# =========================================================

def measure_intensity_robust(image, x, y, radius):
    if radius < 0.5: return np.nan
    if x < radius+1 or x > image.shape[1]-(radius+1) or y < radius+1 or y > image.shape[0]-(radius+1):
        return np.nan
    Y, X = np.ogrid[:image.shape[0], :image.shape[1]]
    dist_from_center = np.sqrt((X - x)**2 + (Y-y)**2)
    mask = dist_from_center <= radius
    return np.mean(image[mask])

# =========================================================
# HAUPT-PIPELINE
# =========================================================

def run_full_analysis(analysis_obj):
    # 1. PFAD LADEN
    entry_id = analysis_obj.Entry_id
    
    # HIER WAR DER FEHLER: Der Import muss oben stehen, der Aufruf hier.
    file_path = Load_MFP_Path(entry_id)
    
    # 2. PARAMETER
    DIAMETER = analysis_obj.Particle_Diameter
    THRESHOLD = analysis_obj.Threshold
    DETECT_CH = getattr(analysis_obj, 'Detect_Channel', 0)
    MIN_DIST = getattr(analysis_obj, 'Min_Dist', 70)
    NOISE_SIZE = getattr(analysis_obj, 'Noise_Size', 3.0)
    MEASURE_CH = 1 if DETECT_CH == 2 else 0 
    
    print(f"--- STARTE FULL ANALYSE (ID: {entry_id}) ---")
    print(f"File: {file_path}")

    if not file_path or not os.path.exists(file_path): 
        return False, f"Datei nicht gefunden: {file_path}"

    # 3. VIDEO LADEN
    with nd2.ND2File(file_path) as nd_file:
        full_data = nd_file.asarray()
        if full_data.ndim == 5: 
             vid_detect = np.max(full_data[:, :, DETECT_CH, :, :], axis=1)
             vid_measure = np.max(full_data[:, :, MEASURE_CH, :, :], axis=1)
        elif full_data.ndim == 4: 
             vid_detect = full_data[:, DETECT_CH, :, :]
             vid_measure = full_data[:, MEASURE_CH, :, :]
        else:
             vid_detect = full_data
             vid_measure = full_data

    # 4. TRACKING LOOP
    all_frames_features = []
    
    # tqdm Ladebalken
    print("Starte Tracking...")
    for t, frame in enumerate(tqdm(vid_detect, desc="Processing", unit="frame")):
        
        _, df_final, _ = process_single_frame(
            frame, 
            diameter=DIAMETER, 
            threshold=THRESHOLD, 
            min_dist=MIN_DIST, 
            noise_size=NOISE_SIZE
        )
        
        if not df_final.empty:
            df_final['frame'] = t
            all_frames_features.append(df_final)

    if not all_frames_features:
        return False, "Keine Partikel gefunden."

    features = pd.concat(all_frames_features, ignore_index=True)

    # 5. LINKING
    print(f"\nLinking {len(features)} Features...")
    tracks = tp.link(features, search_range=30, memory=3)
    tracks = tp.filter_stubs(tracks, threshold=5)
    
    # Stats
    ratio = 0
    if 'valid_fit' in tracks.columns:
        n_total = len(tracks)
        n_valid = tracks['valid_fit'].sum()
        if n_total > 0: ratio = (n_valid / n_total) * 100
        print(f"Qualität: {ratio:.1f}% valid radii")

    # 6. MESSEN (Intensität & Brightfield Radius)
    print("Messe Intensitäten und Brightfield-Radien...")
    intensities = []
    bf_radii = []
    bf_valid_list = []
    
    for idx, row in tqdm(tracks.iterrows(), total=tracks.shape[0], desc="Measuring", unit="spot"):
        # 6a. Intensität messen (wie bisher)
        r_to_measure = row['real_size'] * 0.5
        frame_idx = int(row['frame'])
        val = measure_intensity_robust(vid_measure[frame_idx], row['x'], row['y'], r_to_measure)
        intensities.append(val)
        
        # 6b. NEU: Brightfield Kante (Radius) messen
        # Wir nutzen den MEASURE_CH (Kanal 0, Brightfield) dafür
        # Wir übergeben die `real_size` (Fluo-Sigma) als Start-Schätzung
        bf_img = vid_measure[frame_idx] 
        r_bf, bf_valid = find_edge_in_channel0(bf_img, row['x'], row['y'], row['real_size'])
        
        bf_radii.append(r_bf)
        bf_valid_list.append(bf_valid)

    tracks['intensity_measure'] = intensities
    tracks['radius_brightfield'] = bf_radii
    tracks['radius_brightfield_valid'] = bf_valid_list

    # 7. SPEICHERN
    base_dir = os.path.dirname(file_path)
    analysis_dir = os.path.join(base_dir, "Analysis")
    if not os.path.exists(analysis_dir): os.makedirs(analysis_dir)
        
    output_file = os.path.join(analysis_dir, "tracking_data.pkl")
    
    export_data = {
        'tracks': tracks, 
        'source_file': file_path,
        'parameters': {
            'diameter': DIAMETER, 'threshold': THRESHOLD, 
            'min_dist': MIN_DIST, 'noise_size': NOISE_SIZE
        }
    }
    
    with open(output_file, 'wb') as f:
        pickle.dump(export_data, f)

    # Optional: Speichere auch als CSV für einfache Durchsicht
    csv_output = os.path.join(analysis_dir, "tracking_data.csv")
    tracks.to_csv(csv_output, index=False)
    print(f"Zusätzlich als CSV gespeichert: {csv_output}")

    # analysis_obj.Result_Path = output_file # Auskommentiert, falls du es nicht in der DB brauchst, sonst drinnen lassen
    # analysis_obj.save()
    
    return True, f"Erfolg! {tracks['particle'].nunique()} Spuren."

run_analysis = run_full_analysis