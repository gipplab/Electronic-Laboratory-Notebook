import os
import sys
import concurrent.futures
import multiprocessing

# --- 1. DJANGO INITIALISIERUNG GANZ OBEN ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings')

import django
from django.apps import apps 

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
from Analysis.scripts.MFP_Tracking_Logic import process_single_frame

from skimage.segmentation import active_contour
from skimage.filters import gaussian, sobel
from scipy.ndimage import center_of_mass

from skimage.filters import gaussian
from skimage.feature import canny
from skimage.transform import hough_circle, hough_circle_peaks

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
    
    x_min, x_max = max(0, x_int - r_int), min(w, x_int + r_int + 1)
    y_min, y_max = max(0, y_int - r_int), min(h, y_int + r_int + 1)
    
    roi = image[y_min:y_max, x_min:x_max]
    
    if roi.size == 0: 
        return np.nan
    
    Y, X = np.ogrid[:roi.shape[0], :roi.shape[1]]
    loc_x, loc_y = x - x_min, y - y_min
    mask = (X - loc_x)**2 + (Y - loc_y)**2 <= radius**2
    
    return np.mean(roi[mask])


def _process_single_frame_worker(args):
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings') 
    django.setup()

    f_idx, frame_img, diameter, threshold, min_dist, noise_size = args
    from Analysis.scripts.MFP_Tracking_Logic import process_single_frame
    
    _, df, _ = process_single_frame(
        frame_img, diameter=diameter, threshold=threshold, 
        min_dist=min_dist, noise_size=noise_size
    )
    
    if not df.empty:
        df['frame'] = f_idx
    return df

# --- MODUL 1: PARALLELES TRACKING ---
def perform_tracking_parallel(vid_detect, diameter, threshold, min_dist, noise_size):
    num_cores = multiprocessing.cpu_count()
    print(f"🚀 Starte paralleles Tracking auf {num_cores} CPU-Kernen...")
    
    tasks = [(i, vid_detect[i], diameter, threshold, min_dist, noise_size) for i in range(len(vid_detect))]
    all_features = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        results = list(tqdm(executor.map(_process_single_frame_worker, tasks), total=len(tasks), desc="Tracking (Parallel)"))
        
    for df in results:
        if not df.empty:
            all_features.append(df)
            
    if not all_features:
        return pd.DataFrame() 
    return pd.concat(all_features, ignore_index=True)


# --- MODUL 2: LINKING ---
def perform_linking(features, debug_mode):
    print(f"\nLinking {len(features)} Features...")
    if debug_mode == 0:
        tracks = tp.link(features, search_range=50, memory=3)
        tracks = tp.filter_stubs(tracks, threshold=3)
    else:
        print("⚠️ DEBUG-MODUS: Überspringe Tracking-Links (nur 1 Frame vorhanden).")
        features['particle'] = np.arange(len(features))
        tracks = features
    
    if 'valid_fit' in tracks.columns and len(tracks) > 0:
        ratio = (tracks['valid_fit'].sum() / len(tracks)) * 100
        print(f"Qualität: {ratio:.1f}% valid radii")
    return tracks

def _measure_frame_worker(args):
    """
    Diese Funktion läuft parallel auf mehreren Kernen. 
    Sie übernimmt ein einzelnes Frame und misst alle Partikel darauf.
    """
    frame_idx, rows_df, img_bf, img_measure = args
    
    import numpy as np
    from skimage.filters import gaussian
    from skimage.feature import canny
    from skimage.transform import hough_circle, hough_circle_peaks
    
    frame_results = {}
    
    for row in rows_df.itertuples():
        # --- 1. INTENSITÄT (Fluo-Kanal) ---
        radius = row.real_size * 0.5
        x, y = row.x, row.y
        
        if radius < 0.5 or np.isnan(radius): 
            intensity = np.nan
        else:
            h, w = img_measure.shape
            r_int = int(np.ceil(radius))
            x_int, y_int = int(x), int(y)
            
            x_min_f, x_max_f = max(0, x_int - r_int), min(w, x_int + r_int + 1)
            y_min_f, y_max_f = max(0, y_int - r_int), min(h, y_int + r_int + 1)
            
            roi_f = img_measure[y_min_f:y_max_f, x_min_f:x_max_f]
            if roi_f.size == 0: 
                intensity = np.nan
            else:
                Y_f, X_f = np.ogrid[:roi_f.shape[0], :roi_f.shape[1]]
                loc_x_f, loc_y_f = x - x_min_f, y - y_min_f
                mask_f = (X_f - loc_x_f)**2 + (Y_f - loc_y_f)**2 <= radius**2
                intensity = np.mean(roi_f[mask_f])

        # --- 2. HOUGH CIRCLE TRANSFORM (Brightfield-Kanal) ---
        orig_radius = row.real_size
        box_r = int(orig_radius * 2.5) 
        
        y_int_b, x_int_b = int(row.y), int(row.x)
        y_min, y_max = max(0, y_int_b - box_r), min(img_bf.shape[0], y_int_b + box_r)
        x_min, x_max = max(0, x_int_b - box_r), min(img_bf.shape[1], x_int_b + box_r)
        
        roi_bf = img_bf[y_min:y_max, x_min:x_max]
        
        if roi_bf.size == 0 or roi_bf.max() == roi_bf.min():
            frame_results[row.Index] = {
                'intensity_measure': intensity, 'radius_brightfield': orig_radius,
                'radius_brightfield_valid': False, 'bf_center_x': row.x, 'bf_center_y': row.y
            }
            continue

        try:
            roi_norm = (roi_bf - roi_bf.min()) / (roi_bf.max() - roi_bf.min() + 1e-8)
            roi_smooth = gaussian(roi_norm, sigma=1.5)
            edges = canny(roi_smooth, sigma=1.5, low_threshold=0.1, high_threshold=0.3)

            r_start = max(1, int(orig_radius * 0.8))
            r_end = int(orig_radius * 2.5)
            hough_radii = np.arange(r_start, r_end, 1)
            if len(hough_radii) == 0: hough_radii = np.array([max(1, int(orig_radius))])

            hough_res = hough_circle(edges, hough_radii)
            accums, cx_hough, cy_hough, radii_hough = hough_circle_peaks(hough_res, hough_radii, total_num_peaks=5)

            if len(radii_hough) > 0:
                Y_bf, X_bf = np.ogrid[:roi_bf.shape[0], :roi_bf.shape[1]]
                best_cx, best_cy, best_r = cx_hough[0], cy_hough[0], radii_hough[0]
                min_int_val = float('inf')

                for cx_val, cy_val, r_val in zip(cx_hough, cy_hough, radii_hough):
                    ring_mask = np.abs(np.sqrt((X_bf - cx_val)**2 + (Y_bf - cy_val)**2) - r_val) < 1.0
                    if ring_mask.sum() > 0:
                        val = np.mean(roi_smooth[ring_mask])
                        if val < min_int_val:
                            min_int_val = val
                            best_cx, best_cy, best_r = cx_val, cy_val, r_val
                
                global_cx = best_cx + x_min
                global_cy = best_cy + y_min
                bf_valid = True
            else:
                best_r = orig_radius
                global_cx, global_cy = row.x, row.y
                bf_valid = False
                
        except Exception:
            best_r = orig_radius
            global_cx, global_cy = row.x, row.y
            bf_valid = False

        # Speichert das Ergebnis unter dem originalen Index der Tabelle
        frame_results[row.Index] = {
            'intensity_measure': intensity,
            'radius_brightfield': best_r,
            'radius_brightfield_valid': bf_valid,
            'bf_center_x': global_cx,
            'bf_center_y': global_cy
        }
        
    return frame_results

def perform_measurements(tracks, vid_bf, vid_measure, diameter):
    """Modul 3: Misst Intensitäten und findet Brightfield-Radien (PARALLEL!)."""
    print("Messe Intensitäten und finde robuste Brightfield-Radien (Hough Parallel)...")
    
    if tracks is None or tracks.empty:
        return pd.DataFrame()
        
    # --- DER FIX: Trackpy-Chaos aufräumen ---
    tracks = tracks.reset_index(drop=True)
    # ----------------------------------------
        
    # Wir gruppieren die Partikel nach dem Frame. 
    tasks = []
    for frame_idx, df_frame in tracks.groupby('frame'):
        tasks.append((
            int(frame_idx), 
            df_frame, 
            vid_bf[int(frame_idx)], 
            vid_measure[int(frame_idx)]  # <--- HIER vid_measure ÜBERGEBEN!
        ))
        
    num_cores = multiprocessing.cpu_count()
    all_results = {}
    
    # 🚀 Hier startet die parallele Rakete!
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        for frame_res in tqdm(executor.map(_measure_frame_worker, tasks), total=len(tasks), desc="Measuring (Parallel)", unit="frame"):
            # Füge die Ergebnisse der einzelnen Bilder in unser Master-Lexikon ein
            all_results.update(frame_res)
            
    # Wir wandeln das Lexikon wieder in eine Tabelle um...
    res_df = pd.DataFrame.from_dict(all_results, orient='index')
    
    # ...und kleben sie exakt passend an unsere originale Tabelle!
    return pd.concat([tracks, res_df], axis=1)

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
    # KORREKTUR: HIER LADEN WIR DAS RICHTIGE BILD FÜR DIE KANTEN!
    vid_bf = video_data['brightfield']
    vid_measure = video_data['measure'] 
    file_path = video_data['path']
    print(f"File geladen: {file_path}")
    
    # 2. Parameter
    DIAMETER = analysis_obj.Particle_Diameter
    THRESHOLD = analysis_obj.Threshold
    MIN_DIST = getattr(analysis_obj, 'Min_Dist', 70)
    NOISE_SIZE = getattr(analysis_obj, 'Noise_Size', 3.0)

    # 3. Pipeline
    features = perform_tracking_parallel(vid_detect, DIAMETER, THRESHOLD, MIN_DIST, NOISE_SIZE)
    if features.empty: return False, "Keine Partikel gefunden."

    tracks = perform_linking(features, DEBUG_MODE)
    if tracks.empty: return False, "Nach dem Linking blieben keine Partikel übrig."

    # KORREKTUR: WIR ÜBERGEBEN vid_bf (BRIGHTFIELD) ANSTATT vid_measure
    final_tracks = perform_measurements(tracks, vid_bf, vid_measure, DIAMETER)

    # --- 4. SPEICHERN (Gespiegelte Struktur) ---
    # Den originalen Ordner-Pfad holen
    original_dir = os.path.dirname(file_path)
    
    # "01_Videos" im Pfad durch "02_Analysis_Results" austauschen
    analysis_dir = original_dir.replace('01_Videos', '02_Analysis_Results')
    
    # Neuen Ordner (inklusive des Datums-Ordners) erstellen, falls er nicht existiert
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Originalen Dateinamen ohne Endung extrahieren (z.B. "120100_20260239_xy14_100aTc")
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
        
    # Die neuen Pfade mit dem exakten Messdateinamen bauen
    output_pkl = os.path.join(analysis_dir, f"{base_filename}.pkl")
    output_csv = os.path.join(analysis_dir, f"{base_filename}.csv")
    
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