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
        tracks = tp.link(features, search_range=50, memory=1)
        tracks = tp.filter_stubs(tracks, threshold=1)
    else:
        print("⚠️ DEBUG-MODUS: Überspringe Tracking-Links (nur 1 Frame vorhanden).")
        features['particle'] = np.arange(len(features))
        tracks = features
    
    if 'valid_fit' in tracks.columns and len(tracks) > 0:
        ratio = (tracks['valid_fit'].sum() / len(tracks)) * 100
        print(f"Qualität: {ratio:.1f}% valid radii")
    return tracks

def _measure_particle_worker(args):
    """
    Multiprocessing Worker (Pro Partikel):
    Nutzt den schnellen Hough-Algorithmus + CLAHE Fallback.
    Wendet den "Temporal Prior" an: Sucht im neuen Frame ausgehend vom Radius/Zentrum des alten Frames.
    """
    p_id, df_particle, dict_bf, dict_measure = args
    
    import numpy as np
    from skimage.filters import gaussian
    from skimage.feature import canny       # <--- HIER IST DER FIX
    from skimage.transform import hough_circle, hough_circle_peaks
    from skimage import exposure
    import warnings
    
    particle_results = {}
    
    # WICHTIG: Chronologisch sortieren, damit die Historie Sinn macht!
    df_particle = df_particle.sort_values('frame')
    
    # Gedächtnis des Partikels (Temporal Prior)
    prev_r = None
    prev_cx = None
    prev_cy = None
    
    for row in df_particle.itertuples():
        f_idx = int(row.frame)
        img_bf = dict_bf[f_idx]
        img_measure = dict_measure[f_idx]
        
        # =========================================================
        # 1. INTENSITÄT (Fluoreszenz-Kanal) - Unverändert
        # =========================================================
        radius_f = row.real_size * 0.5
        if radius_f < 0.5 or np.isnan(radius_f): 
            intensity = np.nan
        else:
            h, w = img_measure.shape
            r_int = int(np.ceil(radius_f))
            x_min_f, x_max_f = max(0, int(row.x) - r_int), min(w, int(row.x) + r_int + 1)
            y_min_f, y_max_f = max(0, int(row.y) - r_int), min(h, int(row.y) + r_int + 1)
            roi_f = img_measure[y_min_f:y_max_f, x_min_f:x_max_f]
            if roi_f.size == 0: 
                intensity = np.nan
            else:
                Y_f, X_f = np.ogrid[:roi_f.shape[0], :roi_f.shape[1]]
                mask_f = (X_f - (row.x - x_min_f))**2 + (Y_f - (row.y - y_min_f))**2 <= radius_f**2
                intensity = np.mean(roi_f[mask_f])

        # =========================================================
        # 2. HOUGH CIRCLE TRANSFORM (mit Temporal Prior & CLAHE)
        # =========================================================
        # Nutze vorherige Werte als Ausgangspunkt, falls vorhanden!
        expected_r = prev_r if prev_r is not None else row.real_size
        expected_cx = prev_cx if prev_cx is not None else row.x
        expected_cy = prev_cy if prev_cy is not None else row.y
        
        box_r = int(expected_r * 2.5) 
        
        y_min, y_max = max(0, int(expected_cy - box_r)), min(img_bf.shape[0], int(expected_cy + box_r))
        x_min, x_max = max(0, int(expected_cx - box_r)), min(img_bf.shape[1], int(expected_cx + box_r))
        
        roi_bf = img_bf[y_min:y_max, x_min:x_max]
        loc_x, loc_y = expected_cx - x_min, expected_cy - y_min
        
        if roi_bf.size == 0 or roi_bf.max() == roi_bf.min():
            particle_results[row.Index] = {
                'intensity_measure': intensity, 'radius_brightfield': expected_r,
                'radius_brightfield_valid': False, 'bf_center_x': expected_cx, 'bf_center_y': expected_cy
            }
            continue

        # --- DEINE ELEGANTE HOUGH FUNKTION ---
        def find_circle(use_clahe=False):
            roi_norm = (roi_bf - roi_bf.min()) / (roi_bf.max() - roi_bf.min() + 1e-8)
            
            if use_clahe:
                roi_proc = exposure.equalize_adapthist(roi_norm, clip_limit=0.015)
                low_t, high_t = 0.08, 0.22 
            else:
                roi_proc = roi_norm
                low_t, high_t = 0.1, 0.3   
                
            roi_smooth = gaussian(roi_proc, sigma=1.2)
            edges = canny(roi_smooth, sigma=1.2, low_threshold=low_t, high_threshold=high_t)

            # Suchraum massiv eingeengt dank Temporal Prior (viel schneller!)
            r_start = max(1, int(expected_r * 0.8))
            r_end = int(expected_r * 1.5)
            hough_radii = np.arange(r_start, r_end, 1)
            if len(hough_radii) == 0: 
                hough_radii = np.array([max(1, int(expected_r))])

            hough_res = hough_circle(edges, hough_radii)
            accums, cx_hough, cy_hough, radii_hough = hough_circle_peaks(hough_res, hough_radii, total_num_peaks=10)

            if len(radii_hough) == 0: 
                return None, None, None, 0

            Y_bf, X_bf = np.ogrid[:roi_bf.shape[0], :roi_bf.shape[1]]
            best_score = -1
            b_cx, b_cy, b_r = loc_x, loc_y, expected_r

            for accum, cx_val, cy_val, r_val in zip(accums, cx_hough, cy_hough, radii_hough):
                # Harter Prior: Verhindert, dass der Kreis zu anderen Membranen springt
                dist_to_center = np.sqrt((cx_val - loc_x)**2 + (cy_val - loc_y)**2)
                if dist_to_center > expected_r * 0.5: 
                    continue
                    
                dist_mat = np.sqrt((X_bf - cx_val)**2 + (Y_bf - cy_val)**2)
                ring_mask = np.abs(dist_mat - r_val) <= 1.5 
                
                if ring_mask.sum() == 0: continue
                    
                mean_int = np.mean(roi_proc[ring_mask]) 
                score = accum / (mean_int + 0.1)
                
                if score > best_score:
                    best_score = score
                    b_cx, b_cy, b_r = cx_val, cy_val, r_val
            
            coverage = accums[0] if len(accums) > 0 else 0
            return b_cx, b_cy, b_r, coverage

        try:
            # 1. VERSUCH: Standard-Methode
            b_cx, b_cy, best_r, coverage = find_circle(use_clahe=False)

            # 2. VERSUCH: CLAHE-Booster
            if best_r is None or coverage < 0.15 or best_r < expected_r * 0.85:
                b_cx_c, b_cy_c, b_r_c, cov_c = find_circle(use_clahe=True)
                if b_r_c is not None:
                    b_cx, b_cy, best_r, coverage = b_cx_c, b_cy_c, b_r_c, cov_c

            if best_r is not None:
                global_cx = b_cx + x_min
                global_cy = b_cy + y_min
                bf_valid = True
                
                # Historie für das nächste Frame updaten!
                prev_r = best_r
                prev_cx = global_cx
                prev_cy = global_cy
            else:
                raise ValueError("Kein Kreis gefunden.")
                
        except Exception:
            best_r = expected_r
            global_cx, global_cy = expected_cx, expected_cy
            bf_valid = False

        particle_results[row.Index] = {
            'intensity_measure': intensity,
            'radius_brightfield': best_r,
            'radius_brightfield_valid': bf_valid,
            'bf_center_x': global_cx,
            'bf_center_y': global_cy
        }
        
    return particle_results


def perform_measurements(tracks, vid_bf, vid_measure, diameter):
    """Modul 3: Misst Intensitäten und Radien (PARALLEL NACH PARTIKEL-TRACKS)."""
    print("Messe Intensitäten und Radien (Fast Hough + Temporal Prior)...")
    
    if tracks is None or tracks.empty:
        return pd.DataFrame()
        
    tracks = tracks.reset_index(drop=True)
        
    tasks = []
    # GRUPPIERUNG NACH PARTIKEL (Track-basierte Parallelisierung)
    for p_idx, df_particle in tracks.groupby('particle'):
        
        # Memory-Schutz: Wir übergeben dem Worker nur exakt die Frames, 
        # die dieses spezifische Partikel überhaupt benötigt.
        frames_needed = df_particle['frame'].astype(int).unique()
        dict_bf = {f: vid_bf[f] for f in frames_needed}
        dict_measure = {f: vid_measure[f] for f in frames_needed}
        
        tasks.append((
            int(p_idx), 
            df_particle, 
            dict_bf, 
            dict_measure
        ))
        
    num_cores = multiprocessing.cpu_count()
    all_results = {}
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        # TQDM zählt jetzt Tracks statt Frames
        for particle_res in tqdm(executor.map(_measure_particle_worker, tasks), total=len(tasks), desc="Measuring Tracks (Parallel)", unit="track"):
            all_results.update(particle_res)
            
    res_df = pd.DataFrame.from_dict(all_results, orient='index')
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