import os
import sys
import django
import numpy as np
import torch
import math
import pickle
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
# CELLPOSE CEMENT ANALYSE
# =========================================================

class CellposeCementAnalysis:
    """
    Führt Cellpose-basierte Polymersom-Analyse durch.
    Filtert nach Form-Kriterien (Zirkularität, Solidität, Exzentrizität).
    """
    
    # --- FILTER PARAMETER ---
    MIN_CIRCULARITY = 0.85  
    MIN_SOLIDITY = 0.96     
    MAX_ECCENTRICITY = 0.45
    
    def __init__(self, entry_id, diameter=99):
        self.entry_id = entry_id
        self.diameter = diameter
        self.use_apple_gpu = torch.backends.mps.is_available()
        
        # Modell laden
        print("🔬 Lade Cellpose-Modell...")
        model_path = '/Users/simon/01_Experimental/Electronic-Laboratory-Notebook/Private/Cellpose_Trainingsdaten/models/Polymersome_20260411_121237'
        self.model = models.CellposeModel(gpu=self.use_apple_gpu, pretrained_model=model_path)
        
    def analyze_scout_features(self, features_df, video_data):
        """
        Analysiert Trackpy Scout-Features mit Cellpose.
        
        Args:
            features_df: DataFrame mit Scout-Ergebnissen (x, y, ...)
            video_data: Dict mit 'brightfield', 'detect' Videos
            
        Returns:
            dict mit gefilterten Ergebnissen
        """
        img_bf = video_data['brightfield'][0]  # Frame 0
        img_detect = video_data['detect'][0]
        h_img, w_img = img_bf.shape
        
        box_r = int(self.diameter * 1.5)
        final_results = []
        
        print(f"Analysiere {len(features_df)} Scout-Features mit Cellpose...")
        
        for row in features_df.itertuples():
            cx, cy = row.x, row.y
            
            # Bounding-Box berechnen
            x_min = max(0, int(cx - box_r))
            x_max = min(w_img, int(cx + box_r))
            y_min = max(0, int(cy - box_r))
            y_max = min(h_img, int(cy + box_r))
            
            roi_bf = img_bf[y_min:y_max, x_min:x_max]
            roi_detect = img_detect[y_min:y_max, x_min:x_max]
            
            if roi_bf.size == 0 or roi_detect.size == 0:
                final_results.append({
                    'x': cx, 'y': cy, 'valid': False,
                    'radius': None, 'circularity': None, 
                    'solidity': None, 'eccentricity': None
                })
                continue
            
            # --- NORMALISIERUNG ---
            roi_bf_norm = (roi_bf - roi_bf.min()) / (roi_bf.max() - roi_bf.min() + 1e-8)
            roi_bf_boosted = exposure.equalize_adapthist(roi_bf_norm, clip_limit=0.02)
            
            roi_det_norm = (roi_detect - roi_detect.min()) / (roi_detect.max() - roi_detect.min() + 1e-8)
            
            # --- CELLPOSE VORHERSAGE ---
            roi_combined = np.array([roi_bf_boosted, roi_det_norm])
            
            try:
                masks, _, _ = self.model.eval(
                    roi_combined,
                    diameter=self.diameter,
                    flow_threshold=0.4,
                    cellprob_threshold=0.0
                )
            except Exception as e:
                print(f"  ⚠️ Cellpose Fehler bei ({cx:.1f}, {cy:.1f}): {e}")
                final_results.append({
                    'x': cx, 'y': cy, 'valid': False,
                    'radius': None, 'circularity': None,
                    'solidity': None, 'eccentricity': None
                })
                continue
            
            # --- MASKE AUSWERTEN ---
            local_cx = int(cx - x_min)
            local_cy = int(cy - y_min)
            
            if masks.max() > 0:
                best_mask_id = masks[local_cy, local_cx] if local_cy < masks.shape[0] and local_cx < masks.shape[1] else 0
                
                if best_mask_id == 0 and np.any(masks > 0):
                    best_mask_id = np.argmax(np.bincount(masks[masks > 0]))
                
                if best_mask_id > 0:
                    single_mask = (masks == best_mask_id).astype(int)
                    props = regionprops(single_mask)[0]
                    
                    area = props.area
                    perimeter = props.perimeter
                    solidity = props.solidity
                    eccentricity = props.eccentricity
                    
                    radius = math.sqrt(area / np.pi)
                    circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0.0
                    
                    is_valid = (circularity >= self.MIN_CIRCULARITY and 
                               solidity >= self.MIN_SOLIDITY and 
                               eccentricity <= self.MAX_ECCENTRICITY)
                    
                    donut_y_local, donut_x_local = center_of_mass(single_mask)
                    global_x = donut_x_local + x_min
                    global_y = donut_y_local + y_min
                    
                    final_results.append({
                        'x': global_x, 'y': global_y,
                        'radius': float(radius),
                        'circularity': float(circularity),
                        'solidity': float(solidity),
                        'eccentricity': float(eccentricity),
                        'valid': is_valid
                    })
                else:
                    final_results.append({
                        'x': cx, 'y': cy, 'valid': False,
                        'radius': None, 'circularity': None,
                        'solidity': None, 'eccentricity': None
                    })
            else:
                final_results.append({
                    'x': cx, 'y': cy, 'valid': False,
                    'radius': None, 'circularity': None,
                    'solidity': None, 'eccentricity': None
                })
        
        return final_results
    
    def save_results(self, final_results, scout_pkl_path):
        """
        Speichert Cellpose-Ergebnisse parallel zu Scout-Ergebnissen.
        """
        if not scout_pkl_path:
            return None
            
        # Scout PKL ist z.B.: /path/Scout_120100_20260239_xy14_100aTc.pkl
        # Cellpose speichern als: /path/Cellpose_120100_20260239_xy14_100aTc.pkl
        
        base_dir = os.path.dirname(scout_pkl_path)
        base_name = os.path.basename(scout_pkl_path).replace('Scout_', 'Cellpose_')
        cellpose_pkl = os.path.join(base_dir, base_name)
        
        export_data = {
            'polymersomes': final_results,
            'num_valid': len([r for r in final_results if r['valid']]),
            'num_total': len(final_results)
        }
        
        with open(cellpose_pkl, 'wb') as f:
            pickle.dump(export_data, f)
        
        print(f"💾 Cellpose-Ergebnisse gespeichert: {cellpose_pkl}")
        return cellpose_pkl

def run_cellpose_cement_analysis(entry_id, scout_features_df, scout_pkl_path):
    """
    Haupt-Funktion: Wird aus Dash-Callback aufgerufen.
    """
    try:
        # Daten laden
        video_data = Load_MFP_Video(entry_id)
        if not video_data:
            return False, f"Fehler beim Laden von Entry {entry_id}"
        
        # Analyse starten
        analyzer = CellposeCementAnalysis(entry_id, diameter=99)
        final_results = analyzer.analyze_scout_features(scout_features_df, video_data)
        
        # Speichern
        cellpose_pkl = analyzer.save_results(final_results, scout_pkl_path)
        
        valid_count = len([r for r in final_results if r['valid']])
        total_count = len(final_results)
        
        return True, f"✅ Fertig! {valid_count}/{total_count} gültige Polymersomen gefunden."
        
    except Exception as e:
        return False, f"Fehler bei Cellpose-Analyse: {str(e)}"