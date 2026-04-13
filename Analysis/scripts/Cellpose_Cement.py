import os
import sys
import django
import numpy as np
import torch
import math
import pickle
import concurrent.futures  # 🚨 NEU: Für den 5-Minuten-Timer
from scipy.ndimage import center_of_mass
from cellpose import models
from skimage import exposure
from skimage.measure import regionprops
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

# --- DJANGO SETUP ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings')
if not django.apps.apps.ready:
    django.setup()

from Lab_Misc.Load_Data import Load_MFP_Video
from Analysis.models import MFPAnalysis

# =========================================================
# CELLPOSE CEMENT ANALYSE (AI-FIRST PIPELINE)
# =========================================================

class CellposeCementAnalysis:
    
    # Filter-Parameter
    MIN_CIRCULARITY = 0.70  
    MIN_SOLIDITY = 0.85     
    MAX_ECCENTRICITY = 0.85
    
    def __init__(self, entry_id, diameter=99):
        self.entry_id = entry_id
        self.diameter = diameter
        
        self.use_apple_gpu = torch.backends.mps.is_available()
        self.progress_messages = []
        self.log_progress(f"Lade Standardmodell (GPU: {self.use_apple_gpu})...")
        
        model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/Super_Training_Mix/models/cellpose_1775998269.051098'
        self.model = models.CellposeModel(gpu=self.use_apple_gpu, pretrained_model=model_path)

    def log_progress(self, message):
        self.progress_messages.append(message)
        print(f"✓ {message}")
        log_path = f"/tmp/cellpose_progress_{self.entry_id}.txt"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            pass
        
    def analyze_whole_frame(self, video_data, frame_idx):
        img_bf = video_data['brightfield'][frame_idx].copy().astype(float)
        img_detect = video_data['detect'][frame_idx].copy().astype(float)
        
        img_bf_norm = (img_bf - img_bf.min()) / (img_bf.max() - img_bf.min() + 1e-8)
        img_bf_boosted = exposure.equalize_adapthist(img_bf_norm, kernel_size=(350, 350), clip_limit=0.02)
        
        p_low, p_high = np.percentile(img_detect, (0.5, 99.5))
        img_det_norm = exposure.rescale_intensity(img_detect, in_range=(p_low, p_high), out_range=(0.0, 1.0))
        
        img_combined = np.array([img_det_norm, img_bf_boosted])
        
        try:
            masks, _, _ = self.model.eval(
                img_combined, 
                diameter=float(self.diameter),
                flow_threshold=0.7, 
                cellprob_threshold=-3.0
            )
        except Exception as e:
            self.log_progress(f"⚠️ Cellpose Fehler in Frame {frame_idx}: {str(e)}")
            return []
            
        unique_masks = np.unique(masks)[1:] 
        total_found = len(unique_masks)
        
        # =========================================================
        # 🚨 NOTBREMSE 1: ZU VIELE OBJEKTE 🚨
        # =========================================================
        if total_found > 100:
            self.log_progress(f"   Frame {frame_idx:03d}: ⚠️ Abbruch! {total_found} Objekte gefunden (Limit: 100). Frame wird ignoriert.")
            return []
        
        final_results = []
        valid_in_frame = 0
        
        for mask_id in unique_masks:
            single_mask = (masks == mask_id).astype(int)
            props = regionprops(single_mask)[0]
            
            area, perimeter = props.area, props.perimeter
            radius = math.sqrt(area / np.pi)
            circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0.0
            
            is_valid = (circularity >= self.MIN_CIRCULARITY and 
                        props.solidity >= self.MIN_SOLIDITY and 
                        props.eccentricity <= self.MAX_ECCENTRICITY)
            
            if is_valid:
                d_y, d_x = center_of_mass(single_mask)
                valid_in_frame += 1
                
                final_results.append({
                    'frame': frame_idx,
                    'x': float(d_x), 'y': float(d_y),
                    'radius': float(radius), 'circularity': float(circularity),
                    'solidity': float(props.solidity), 'eccentricity': float(props.eccentricity),
                    'valid': True
                })
        
        self.log_progress(f"   Frame {frame_idx:03d}: {total_found} Objekte gefunden, davon {valid_in_frame} valide.")
        return final_results
    
    def save_results(self, final_results, scout_pkl_path):
        base_dir = os.path.dirname(scout_pkl_path) if scout_pkl_path else "/tmp"
        base_name = os.path.basename(scout_pkl_path).replace('Scout_', 'Cellpose_') if scout_pkl_path else f"Cellpose_{self.entry_id}.pkl"
        cellpose_pkl = os.path.join(base_dir, base_name)
        
        try:
            with open(cellpose_pkl, 'wb') as f:
                pickle.dump({'polymersomes': final_results, 'num_total': len(final_results)}, f)
            self.log_progress(f"✅ Ergebnisse gespeichert unter: {cellpose_pkl}")
        except Exception as e:
            self.log_progress(f"⚠️ Speicherfehler: {str(e)}")
        return cellpose_pkl

# =========================================================
# ENTRY POINT FÜR DAS DASHBOARD
# =========================================================
def run_cellpose_cement_analysis(entry_id, diameter, minmass, box_size, target_frame, run_mode, scout_pkl_path=None):
    log_path = f"/tmp/cellpose_progress_{entry_id}.txt"
    if os.path.exists(log_path): os.remove(log_path)
        
    try:
        analyzer = CellposeCementAnalysis(entry_id, diameter=diameter)
        video_data = Load_MFP_Video(entry_id)
        if not video_data:
            analyzer.log_progress("❌ Fehler: Video-Daten konnten nicht geladen werden.")
            return False, "\n".join(analyzer.progress_messages)
        
        num_frames = len(video_data['brightfield'])
        
        if run_mode == 'single':
            analyzer.log_progress(f"🚀 Starte Test-Analyse für Frame {target_frame}...")
            frames_to_process = [int(target_frame)]
        else:
            analyzer.log_progress(f"🚀 Starte Voll-Analyse ({num_frames} Frames)...")
            frames_to_process = range(num_frames)
        
        all_results = []
        for frame_idx in frames_to_process:
            
            # =========================================================
            # 🚨 NOTBREMSE 2: 5-MINUTEN TIMEOUT PRO FRAME 🚨
            # =========================================================
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                # Wir lagern die Analyse in einen Hintergrund-Job aus
                future = executor.submit(analyzer.analyze_whole_frame, video_data, frame_idx)
                
                try:
                    # Wir warten maximal 300 Sekunden (5 Minuten)
                    frame_results = future.result(timeout=300)
                    all_results.extend(frame_results)
                    
                except concurrent.futures.TimeoutError:
                    # Wenn die Zeit abgelaufen ist, brechen wir ab und machen mit dem nächsten Frame weiter
                    analyzer.log_progress(f"   Frame {frame_idx:03d}: ⏱️ KRITISCHER ABBRUCH! Zeitlimit von 5 Minuten überschritten.")
                except Exception as e:
                    analyzer.log_progress(f"   Frame {frame_idx:03d}: ❌ Systemfehler: {str(e)}")
            
        if run_mode != 'single' and len(all_results) > 0:
            analyzer.log_progress("\n🔗 Starte smartes Tracking mit Fluss-Erkennung...")
            
            df = pd.DataFrame(all_results)
            df = df.sort_values('frame')
            
            MAX_DISTANCE = 120.0       
            MAX_RADIUS_CHANGE = 10.0   
            RADIUS_WEIGHT = 2.0       
            MEMORY_FRAMES = 7    
            
            tracked_data = []
            next_track_id = 1
            active_tracks = {} 
            
            for frame_idx, group in df.groupby('frame'):
                current_detections = group.to_dict('records')
                
                if not active_tracks:
                    for det in current_detections:
                        det['particle'] = next_track_id
                        tracked_data.append(det)
                        active_tracks[next_track_id] = {**det, 'lost_count': 0}
                        next_track_id += 1
                    continue
                
                track_ids = list(active_tracks.keys())
                track_coords = np.array([[active_tracks[tid]['x'], active_tracks[tid]['y']] for tid in track_ids])
                track_radii = np.array([active_tracks[tid]['radius'] for tid in track_ids])
                
                det_coords = np.array([[d['x'], d['y']] for d in current_detections])
                det_radii = np.array([d['radius'] for d in current_detections])
                
                drift_x, drift_y = 0.0, 0.0
                if len(track_coords) > 0 and len(det_coords) > 0:
                    dists = cdist(track_coords, det_coords)
                    min_indices = np.argmin(dists, axis=0)
                    drift_x = np.median(det_coords[:, 0] - track_coords[min_indices, 0])
                    drift_y = np.median(det_coords[:, 1] - track_coords[min_indices, 1])
                    
                predicted_track_coords = track_coords + np.array([drift_x, drift_y])
                
                dist_matrix = cdist(predicted_track_coords, det_coords)
                raw_rad_diff = np.abs(track_radii[:, None] - det_radii[None, :])
                cost_matrix = dist_matrix + (raw_rad_diff * RADIUS_WEIGHT)
                
                invalid_links = (dist_matrix > MAX_DISTANCE) | (raw_rad_diff > MAX_RADIUS_CHANGE)
                cost_matrix[invalid_links] = 1e9
                
                row_ind, col_ind = linear_sum_assignment(cost_matrix)
                
                assigned_detections = set()
                new_active_tracks = {}
                
                for r, c in zip(row_ind, col_ind):
                    if cost_matrix[r, c] < 1e9: 
                        tid = track_ids[r]
                        det = current_detections[c]
                        det['particle'] = tid
                        tracked_data.append(det)
                        new_active_tracks[tid] = {**det, 'lost_count': 0}
                        assigned_detections.add(c)
                
                for c, det in enumerate(current_detections):
                    if c not in assigned_detections:
                        det['particle'] = next_track_id
                        tracked_data.append(det)
                        new_active_tracks[next_track_id] = {**det, 'lost_count': 0}
                        next_track_id += 1
                
                for tid, track_info in active_tracks.items():
                    if tid not in new_active_tracks:
                        track_info['lost_count'] += 1
                        if track_info['lost_count'] <= MEMORY_FRAMES:
                            track_info['x'] += drift_x
                            track_info['y'] += drift_y
                            new_active_tracks[tid] = track_info
                
                active_tracks = new_active_tracks
            
            all_results = tracked_data
            unique_tracks = len(set(d['particle'] for d in tracked_data))
            analyzer.log_progress(f"🔗 Tracking abgeschlossen! {unique_tracks} perfekte Zell-Pfade generiert.")
            
        analyzer.save_results(all_results, scout_pkl_path)
        
        analyzer.log_progress(f"\n🎉 ANALYSE ERFOLGREICH BEENDET!")
        return True, "\n".join(analyzer.progress_messages)
        
    except Exception as e:
        import traceback
        return False, f"❌ Systemfehler: {str(e)}\n{traceback.format_exc()}"