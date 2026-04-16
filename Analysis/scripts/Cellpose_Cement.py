import os
import sys
import django
import numpy as np
import torch
import math
import pickle
import time
import psutil
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

from Lab_Misc.Load_Data import Load_MFP_Video, Load_MFP_Path
from Analysis.models import MFPAnalysis

# =========================================================
# 1. DER SERVER-TÜRSTEHER (Ressourcen-Check)
# =========================================================
def wait_for_free_resources(required_ram_gb=10, required_vram_gb=4, max_cpu_percent=85, log_file=None):
    def _log(msg):
        print(msg)
        if log_file:
            try:
                with open(log_file, "a") as f:
                    f.write(msg + "\n")
            except:
                pass

    _log("🔍 Prüfe Server-Auslastung vor dem Start...")
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        free_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        free_vram_gb = 100 
        if torch.cuda.is_available():
            free_vram, _ = torch.cuda.mem_get_info()
            free_vram_gb = free_vram / (1024 ** 3)
            
        if cpu_usage < max_cpu_percent and free_ram_gb > required_ram_gb and free_vram_gb > required_vram_gb:
            _log(f"✅ Ressourcen frei! (CPU: {cpu_usage}%, RAM: {free_ram_gb:.1f}GB, VRAM: {free_vram_gb:.1f}GB)")
            return True 
        else:
            _log(f"⚠️ Server ausgelastet. Warte 60 Sekunden...")
            time.sleep(60)

# =========================================================
# 2. CELLPOSE CEMENT ANALYSE
# =========================================================
class CellposeCementAnalysis:
    MIN_CIRCULARITY = 0.70  
    MIN_SOLIDITY = 0.85     
    MAX_ECCENTRICITY = 0.85
    
    def __init__(self, entry_id, diameter=99):
        self.entry_id = entry_id
        self.diameter = diameter
        
        # GPU Limitierung für den Worker (max 15% VRAM pro Prozess)
        if torch.cuda.is_available():
            torch.cuda.set_per_process_memory_fraction(0.15)
        self.use_gpu = torch.cuda.is_available() or torch.backends.mps.is_available()
        
        self.progress_messages = []
        self.log_progress(f"Lade Standardmodell (GPU: {self.use_gpu})...")
        
        model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/Super_Training_Mix/models/cellpose_1775998269.051098'
        self.model = models.CellposeModel(gpu=self.use_gpu, pretrained_model=model_path)

    def log_progress(self, message):
        self.progress_messages.append(message)
        print(f"✓ {message}")
        try:
            with open(f"/tmp/cellpose_log_{self.entry_id}.txt", "a") as f:
                f.write(f"✓ {message}\n")
        except:
            pass
        
    def analyze_whole_frame(self, video_data, frame_idx):
        img_bf = video_data['brightfield'][frame_idx].copy().astype(float)
        img_detect = video_data['detect'][frame_idx].copy().astype(float)
        
        try:
            img_measure = video_data['measure'][frame_idx].copy().astype(float)
        except:
            img_measure = img_detect

        img_bf_norm = (img_bf - img_bf.min()) / (img_bf.max() - img_bf.min() + 1e-8)
        img_bf_boosted = exposure.equalize_adapthist(img_bf_norm, kernel_size=(350, 350), clip_limit=0.02)
        
        p_low, p_high = np.percentile(img_detect, (0.5, 99.5))
        img_det_norm = exposure.rescale_intensity(img_detect, in_range=(p_low, p_high), out_range=(0.0, 1.0))
        img_combined = np.array([img_det_norm, img_bf_boosted])
        
        try:
            masks, _, _ = self.model.eval(img_combined, diameter=float(self.diameter), flow_threshold=0.7, cellprob_threshold=-3.0)
        except Exception as e:
            self.log_progress(f"⚠️ Cellpose Fehler in Frame {frame_idx}: {str(e)}")
            return []
            
        unique_masks = np.unique(masks)[1:] 
        total_found = len(unique_masks)
        
        # NOTBREMSE 1: ZU VIELE OBJEKTE
        if total_found > 100:
            self.log_progress(f"   Frame {frame_idx:03d}: ⚠️ {total_found} Objekte gefunden (Limit: 100).")
            if frame_idx < 2:
                raise ValueError(f"IMPLAUSIBLE: Zu viele Objekte ({total_found}) im Start-Frame {frame_idx}. Verdacht auf Rauschen/falsche Parameter. Analyse wird komplett abgebrochen!")
            self.log_progress(f"   Frame {frame_idx:03d} wird ignoriert.")
            return []
        
        final_results = []
        valid_in_frame = 0
        
        for mask_id in unique_masks:
            single_mask = (masks == mask_id).astype(int)
            props = regionprops(single_mask)[0]
            
            area, perimeter = props.area, props.perimeter
            radius = math.sqrt(area / np.pi)
            circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0.0
            
            is_valid = (circularity >= self.MIN_CIRCULARITY and props.solidity >= self.MIN_SOLIDITY and props.eccentricity <= self.MAX_ECCENTRICITY)
            
            if is_valid:
                d_y, d_x = center_of_mass(single_mask)
                valid_in_frame += 1

                # === NEU: BEIDE INTENSITÄTEN BERECHNEN ===
                try:
                    intensity_measure = np.mean(img_measure[single_mask == 1])
                except:
                    intensity_measure = 0.0
                    
                try:
                    intensity_detect = np.mean(img_detect[single_mask == 1])
                except:
                    intensity_detect = 0.0

                final_results.append({
                    'frame': frame_idx, 'x': float(d_x), 'y': float(d_y),
                    'radius': float(radius), 'circularity': float(circularity),
                    'solidity': float(props.solidity), 'eccentricity': float(props.eccentricity), 'valid': True,
                    'intensity_measure': float(intensity_measure), # mScarlet
                    'intensity_detect': float(intensity_detect),   # GFP
                    'radius_brightfield': float(radius),
                    'real_size': float(radius)
                })
        
        self.log_progress(f"   Frame {frame_idx:03d}: {total_found} Objekte gefunden, davon {valid_in_frame} valide.")
        return final_results

# =========================================================
# 3. DER BACKGROUND-WORKER JOB
# =========================================================
def run_cellpose_cement_analysis(entry_id, diameter, minmass=None, box_size=None, target_frame=None, run_mode='all', scout_pkl_path=None):
    """
    Diese Funktion wird vom Django-Q2 Cluster aufgerufen.
    """
    log_file = f"/tmp/cellpose_log_{entry_id}.txt"
    try:
        with open(log_file, "w") as f:
            f.write(f"--- Starte Cellpose Analyse für ID {entry_id} ---\n")
    except:
        pass

    # 🚨 1. TÜRSTEHER FRAGEN BEVOR ES LOSGEHT
    wait_for_free_resources(required_ram_gb=10, required_vram_gb=4, max_cpu_percent=85, log_file=log_file)
    
    analysis_obj, _ = MFPAnalysis.objects.get_or_create(Entry_id=entry_id)
    analysis_obj.status = MFPAnalysis.Status.NOT_STARTED # In Processing setzen (falls du den Status hast, sonst lass es so)
    analysis_obj.save()
    
    try:
        analyzer = CellposeCementAnalysis(entry_id, diameter=diameter)
        video_data = Load_MFP_Video(entry_id)
        if not video_data:
            raise ValueError("Video-Daten konnten nicht geladen werden.")
        
        num_frames = len(video_data['brightfield'])
        frames_to_process = [int(target_frame)] if run_mode == 'single' else range(num_frames)
        
        all_results = []
        for frame_idx in frames_to_process:
            # 🚨 HIER KEIN TIMEOUT MEHR - DJANGO-Q2 REGELT DAS!
            frame_results = analyzer.analyze_whole_frame(video_data, frame_idx)
            all_results.extend(frame_results)
            
        if run_mode != 'single' and len(all_results) > 0:
            analyzer.log_progress("\n🔗 Starte smartes Tracking mit Fluss-Erkennung...")
            df = pd.DataFrame(all_results).sort_values('frame')
            
            MAX_DISTANCE, MAX_RADIUS_CHANGE, RADIUS_WEIGHT, MEMORY_FRAMES = 120.0, 10.0, 2.0, 7    
            
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

        # 🚨 2. DEN SICHEREN SPEICHERORT GENERIEREN
        from Lab_Misc import General

        # rel_link = analysis_obj.Entry.Link # OLD, BROKEN: 'MFP' object has no attribute 'Link'
        # NEW: Get absolute path from helper and make it relative for saving.
        abs_video_path = Load_MFP_Path(analysis_obj.Entry.id)
        base_path = General.get_BasePath()
        rel_link = os.path.relpath(abs_video_path, base_path) if abs_video_path and abs_video_path.startswith(base_path) else None

        if rel_link and "01_Videos" in rel_link:
            rel_pkl = rel_link.replace("01_Videos", "02_Analysis_Results").rsplit('.', 1)[0] + '.pkl'
            abs_pkl = os.path.join(General.get_BasePath(), rel_pkl)
            os.makedirs(os.path.dirname(abs_pkl), exist_ok=True)
        else:
            rel_pkl = f"/tmp/Cellpose_{entry_id}.pkl"
            abs_pkl = rel_pkl
            
        with open(abs_pkl, 'wb') as f:
            pickle.dump({'polymersomes': all_results, 'num_total': len(all_results)}, f)
            
        # 🚨 2b. CSV speichern, damit Load_MFP die Daten findet und die Zeitachse (time) hinzufügt
        if len(all_results) > 0 and run_mode != 'single':
            abs_csv = abs_pkl.replace('.pkl', '.csv')
            pd.DataFrame(all_results).to_csv(abs_csv, index=False)

        # 🚨 3. DATENBANK AKTUALISIEREN & PLAUSIBILITÄT PRÜFEN
        if len(all_results) > 0 and run_mode != 'single':
            df_tracked = pd.DataFrame(all_results)
            first_frame = df_tracked['frame'].min()
            particles_start = df_tracked[df_tracked['frame'] == first_frame]['particle'].nunique()
            
            analysis_obj.total_particles = df_tracked['particle'].nunique()
            analysis_obj.Result_Path = rel_pkl
            
            if particles_start < 5:
                analysis_obj.status = MFPAnalysis.Status.IMPLAUSIBLE
                analysis_obj.is_plausible = False
                analysis_obj.warning_message = f"Nur {particles_start} Partikel im ersten Frame."
            else:
                analysis_obj.status = MFPAnalysis.Status.COMPLETED
                analysis_obj.is_plausible = True
                analysis_obj.warning_message = ""
                analysis_obj.error_message = ""
        
        analysis_obj.save()
        try:
            with open(log_file, "a") as f:
                f.write("✅ Analyse erfolgreich abgeschlossen!\n")
        except:
            pass
        return True, "\n".join(analyzer.progress_messages)
        
    except Exception as e:
        import traceback
        
        if str(e).startswith("IMPLAUSIBLE:"):
            analysis_obj.status = MFPAnalysis.Status.IMPLAUSIBLE
            analysis_obj.is_plausible = False
            analysis_obj.warning_message = str(e).replace("IMPLAUSIBLE: ", "")
            analysis_obj.save()
            try:
                with open(log_file, "a") as f:
                    f.write(f"⚠️ {analysis_obj.warning_message}\n")
            except:
                pass
            return False, f"⚠️ {analysis_obj.warning_message}"
            
        analysis_obj.status = MFPAnalysis.Status.FAILED
        analysis_obj.error_message = f"Fehler: {str(e)}"
        analysis_obj.is_plausible = False
        analysis_obj.save()
        try:
            with open(log_file, "a") as f:
                f.write(f"❌ Systemfehler: {str(e)}\n{traceback.format_exc()}\n")
        except:
            pass
        return False, f"❌ Systemfehler: {str(e)}\n{traceback.format_exc()}"