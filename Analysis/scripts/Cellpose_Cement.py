import os
import sys
import django
import numpy as np
import torch
import math
import pickle
import trackpy as tp  # <--- NEU: Trackpy ist jetzt direkt hier!
from scipy.ndimage import center_of_mass
from cellpose import models
from skimage import exposure
from skimage.measure import regionprops

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Private.settings')
if not django.apps.apps.ready:
    django.setup()

from Lab_Misc.Load_Data import Load_MFP_Video
from Analysis.models import MFPAnalysis

# =========================================================
# CELLPOSE CEMENT ANALYSE (ALLE FRAMES)
# =========================================================

class CellposeCementAnalysis:
    
    MIN_CIRCULARITY = 0.85  
    MIN_SOLIDITY = 0.96     
    MAX_ECCENTRICITY = 0.45
    
    # ACHTUNG: frame_idx wurde hier entfernt, da wir jetzt loopen!
    def __init__(self, entry_id, diameter=99):
        self.entry_id = entry_id
        self.diameter = diameter
        self.use_apple_gpu = torch.backends.mps.is_available()
        self.progress_messages = []
        
        self.log_progress("Lade Cellpose-Modell in den M3-Speicher...")
        model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/models/Polymersome_20260411_121237'
        self.model = models.CellposeModel(gpu=self.use_apple_gpu, pretrained_model=model_path)
        
    def log_progress(self, message):
        self.progress_messages.append(message)
        print(f"✓ {message}")
        
    # ACHTUNG: frame_idx wird jetzt pro Aufruf übergeben!
    def analyze_scout_features(self, features_df, video_data, frame_idx):
        img_bf = video_data['brightfield'][frame_idx]
        img_detect = video_data['detect'][frame_idx]
        h_img, w_img = img_bf.shape
        
        box_r = int(self.diameter * 1.5)
        final_results = []
        
        for idx, row in enumerate(features_df.itertuples()):
            cx, cy = row.x, row.y
            
            x_min, x_max = max(0, int(cx - box_r)), min(w_img, int(cx + box_r))
            y_min, y_max = max(0, int(cy - box_r)), min(h_img, int(cy + box_r))
            
            roi_bf = img_bf[y_min:y_max, x_min:x_max]
            roi_detect = img_detect[y_min:y_max, x_min:x_max]
            
            if roi_bf.size == 0 or roi_detect.size == 0:
                continue
            
            roi_bf_norm = (roi_bf - roi_bf.min()) / (roi_bf.max() - roi_bf.min() + 1e-8)
            roi_bf_boosted = exposure.equalize_adapthist(roi_bf_norm, clip_limit=0.02)
            roi_det_norm = (roi_detect - roi_detect.min()) / (roi_detect.max() - roi_detect.min() + 1e-8)
            
            roi_combined = np.array([roi_bf_boosted, roi_det_norm])
            
            try:
                masks, _, _ = self.model.eval(roi_combined, diameter=self.diameter, flow_threshold=0.4, cellprob_threshold=0.0)
            except Exception:
                continue
            
            local_cx, local_cy = int(cx - x_min), int(cy - y_min)
            
            if masks.max() > 0:
                best_mask_id = masks[local_cy, local_cx] if local_cy < masks.shape[0] and local_cx < masks.shape[1] else 0
                if best_mask_id == 0 and np.any(masks > 0):
                    best_mask_id = np.argmax(np.bincount(masks[masks > 0]))
                
                if best_mask_id > 0:
                    single_mask = (masks == best_mask_id).astype(int)
                    props = regionprops(single_mask)[0]
                    
                    area, perimeter = props.area, props.perimeter
                    radius = math.sqrt(area / np.pi)
                    circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0.0
                    
                    is_valid = (circularity >= self.MIN_CIRCULARITY and props.solidity >= self.MIN_SOLIDITY and props.eccentricity <= self.MAX_ECCENTRICITY)
                    
                    d_y, d_x = center_of_mass(single_mask)
                    
                    final_results.append({
                        'frame': frame_idx,  # <--- WICHTIG: Frame-ID mitspeichern!
                        'x': d_x + x_min, 'y': d_y + y_min,
                        'radius': float(radius), 'circularity': float(circularity),
                        'solidity': float(props.solidity), 'eccentricity': float(props.eccentricity),
                        'valid': is_valid
                    })
        return final_results
    
    def save_results(self, final_results, scout_pkl_path):
        self.log_progress("Speichere aggregierte Ergebnisse aller Frames...")
        base_dir = os.path.dirname(scout_pkl_path) if scout_pkl_path else "/tmp"
        base_name = os.path.basename(scout_pkl_path).replace('Scout_', 'Cellpose_') if scout_pkl_path else f"Cellpose_{self.entry_id}.pkl"
        cellpose_pkl = os.path.join(base_dir, base_name)
        
        try:
            with open(cellpose_pkl, 'wb') as f:
                pickle.dump({'polymersomes': final_results, 'num_total': len(final_results)}, f)
            self.log_progress(f"✅ Datei gespeichert: {cellpose_pkl}")
        except Exception as e:
            self.log_progress(f"⚠️ Speicherfehler: {str(e)}")
        return cellpose_pkl

# =========================================================
# DIE NEUE MASTER-FUNKTION (Loop über alle Frames)
# =========================================================
def run_cellpose_cement_analysis(entry_id, diameter, minmass, scout_pkl_path=None):
    try:
        analyzer = CellposeCementAnalysis(entry_id, diameter=diameter)
        analyzer.log_progress("🚀 Starte Cellpose Bulk-Analyse für ALLE Frames...")
        
        video_data = Load_MFP_Video(entry_id)
        if not video_data:
            analyzer.log_progress("❌ Fehler: Konnte Video-Daten nicht laden")
            return False, "\n".join(analyzer.progress_messages)
        
        num_frames = len(video_data['brightfield'])
        analyzer.log_progress(f"📹 Video gefunden: {num_frames} Frames werden verarbeitet.")
        
        all_results = []
        
        # --- DIE MASTER-SCHLEIFE ---
        for frame_idx in range(num_frames):
            img_detect = video_data['detect'][frame_idx]
            dia = diameter if diameter % 2 != 0 else diameter + 1
            
            # 1. SCOUT (auf dem aktuellen Frame)
            features = tp.locate(img_detect, diameter=dia, minmass=minmass)
            
            if features.empty:
                analyzer.log_progress(f"   ⚠️ Frame {frame_idx:03d}: Scout fand 0 Punkte.")
                continue
                
            # 2. CELLPOSE (auf dem aktuellen Frame)
            frame_results = analyzer.analyze_scout_features(features, video_data, frame_idx)
            all_results.extend(frame_results)
            
            # Kurzes Update ins Log
            valid_in_frame = len([r for r in frame_results if r['valid']])
            analyzer.log_progress(f"   ✓ Frame {frame_idx:03d}: {valid_in_frame}/{len(features)} gültige Zellen.")
        
        # Speichern & Abschluss
        analyzer.save_results(all_results, scout_pkl_path)
        valid_count = len([r for r in all_results if r['valid']])
        
        analyzer.log_progress(f"\n🎉 ALLE FRAMES FERTIG!")
        analyzer.log_progress(f"✅ Insgesamt {valid_count} perfekte Polymersomen im ganzen Video gefunden.")
        
        return True, "\n".join(analyzer.progress_messages)
        
    except Exception as e:
        import traceback
        return False, f"❌ Fehler: {str(e)}\n{traceback.format_exc()}"