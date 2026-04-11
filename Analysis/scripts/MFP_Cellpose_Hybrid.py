import numpy as np
import math
import trackpy as tp
import torch
from scipy.ndimage import center_of_mass
from cellpose import models
from skimage import exposure
from skimage.measure import regionprops
from Lab_Misc.Load_Data import Load_MFP_Video

def run_hybrid_cellpose_test(entry_id, frame_idx, diameter, minmass, model_path):
    # 1. DATEN LADEN
    video_data = Load_MFP_Video(entry_id)
    img_detect = video_data['detect'][frame_idx].copy()
    img_bf = video_data['brightfield'][frame_idx].copy()
    h_img, w_img = img_bf.shape

    # 2. SCHRITT A: SCOUT (Trackpy)
    features = tp.locate(img_detect, diameter=diameter, minmass=minmass)
    if len(features) == 0 or len(features) > 300:
        return {"status": "error", "message": f"Trackpy fand {len(features)} Punkte. Bitte MinMass anpassen!"}

    # 3. SCHRITT B: CELLPOSE
    use_apple_gpu = torch.backends.mps.is_available()
    model = models.CellposeModel(gpu=use_apple_gpu, pretrained_model=model_path)
    
    box_r = int(diameter * 1.5) 
    final_results = []
    
    for row in features.itertuples():
        cx, cy = row.x, row.y
        x_min, x_max = max(0, int(cx - box_r)), min(w_img, int(cx + box_r))
        y_min, y_max = max(0, int(cy - box_r)), min(h_img, int(cy + box_r))
        
        roi_bf = img_bf[y_min:y_max, x_min:x_max]
        roi_detect = img_detect[y_min:y_max, x_min:x_max] 
        
        if roi_bf.size == 0 or roi_detect.size == 0: continue
            
        roi_bf_norm = (roi_bf - roi_bf.min()) / (roi_bf.max() - roi_bf.min() + 1e-8)
        roi_boosted = exposure.equalize_adapthist(roi_bf_norm, clip_limit=0.02)
        roi_det_norm = (roi_detect - roi_detect.min()) / (roi_detect.max() - roi_detect.min() + 1e-8)
            
        roi_combined = np.array([roi_boosted, roi_det_norm])
            
        masks, _, _ = model.eval(roi_combined, diameter=diameter, flow_threshold=0.4, cellprob_threshold=0.0)
        
        if masks.max() > 0:
            local_cx, local_cy = int(cx - x_min), int(cy - y_min)
            best_mask_id = masks[local_cy, local_cx]
            if best_mask_id == 0: best_mask_id = np.argmax(np.bincount(masks[masks > 0]))
                
            single_mask = (masks == best_mask_id).astype(int)
            props = regionprops(single_mask)[0]
            
            circularity = (4 * np.pi * props.area) / (props.perimeter ** 2) if props.perimeter > 0 else 0.0
            
            # Harte Filter (wie in deinem Skript)
            if circularity >= 0.85 and props.solidity >= 0.96 and props.eccentricity <= 0.45:
                d_y, d_x = center_of_mass(single_mask)
                final_results.append({
                    'x': d_x + x_min, 'y': d_y + y_min, 
                    'radius': math.sqrt(props.area / np.pi)
                })

    # Du kannst hier entweder die Koordinaten zurückgeben oder ein Preview-Bild speichern
    return {
        "status": "success", 
        "found_points": len(features),
        "valid_cells": len(final_results),
        "data": final_results
    }