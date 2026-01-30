import numpy as np
import trackpy as tp
import pandas as pd
from scipy.optimize import curve_fit

# --- MATHEMATIK ---

def gaussian_2d_fixed_center(xy, amplitude, sigma, offset, fixed_x, fixed_y):
    x, y = xy
    g = offset + amplitude * np.exp(-((x - fixed_x)**2 + (y - fixed_y)**2) / (2 * sigma**2))
    return g.ravel()

def fit_spot_position_strict(image, center_x, center_y, radius=25):
    """Findet exakte Sub-Pixel Position."""
    y_int, x_int = int(center_y), int(center_x)
    if y_int < 0 or x_int < 0 or y_int >= image.shape[0] or x_int >= image.shape[1]: return None
    
    y_min, y_max = max(0, y_int - radius), min(image.shape[0], y_int + radius)
    x_min, x_max = max(0, x_int - radius), min(image.shape[1], x_int + radius)
    roi = image[y_min:y_max, x_min:x_max]
    
    if roi.size < 25: return None
    
    xx, yy = np.meshgrid(np.arange(x_min, x_max), np.arange(y_min, y_max))
    p0 = [roi.max()-roi.min(), center_x, center_y, 5.0, roi.min()]
    
    try:
        popt, _ = curve_fit(lambda xy, a, x0, y0, s, off: gaussian_2d_fixed_center(xy, a, s, off, x0, y0), 
                            (xx, yy), roi.ravel(), p0=p0,
                            bounds=([0, x_min, y_min, 1, 0], [np.inf, x_max, y_max, 25, np.inf]), maxfev=600)
        return {'x': popt[1], 'y': popt[2], 'amplitude': popt[0]} 
    except: return None

def measure_radius_at_fixed_pos(image, x, y, guess_diameter):
    """
    Misst Radius.
    Returns: (Radius_Value, Is_Valid_Fit)
    """
    box_r = int(guess_diameter)
    y_int, x_int = int(y), int(x)
    y_min, y_max = max(0, y_int - box_r), min(image.shape[0], y_int + box_r)
    x_min, x_max = max(0, x_int - box_r), min(image.shape[1], x_int + box_r)
    roi = image[y_min:y_max, x_min:x_max]
    
    # Fallback 1: ROI zu klein
    if roi.size < 25: return float(guess_diameter) * 0.3, False 
    
    xx, yy = np.meshgrid(np.arange(x_min, x_max), np.arange(y_min, y_max))
    guess_sigma = max(1.5, guess_diameter / 6.0)
    p0 = [roi.max()-roi.min(), guess_sigma, roi.min()]
    max_sigma = max(3.0, guess_diameter * 0.5)
    
    try:
        popt, _ = curve_fit(lambda xy, a, s, off: gaussian_2d_fixed_center(xy, a, s, off, x, y),
                            (xx, yy), roi.ravel(), p0=p0, 
                            bounds=([0, 0.5, 0], [np.inf, max_sigma, np.inf]))
        sigma = popt[1]
        
        # SUCCESS: Wir haben einen echten Wert (Faktor 1.0)
        return sigma * 1.0, True
    except: 
        # FAILURE: Wir nehmen Fallback
        return float(guess_diameter) * 0.3, False

def aggregate_simple(df, min_dist):
    if len(df) == 0: return df
    pending = df.sort_values('amplitude', ascending=False).copy()
    consolidated = []
    while len(pending) > 0:
        seed = pending.iloc[0]
        dists = np.sqrt((pending['x'] - seed['x'])**2 + (pending['y'] - seed['y'])**2)
        cluster = pending[dists < min_dist]
        weights = cluster['amplitude']
        total_w = weights.sum()
        if total_w > 0:
            new_x, new_y = (cluster['x']*weights).sum()/total_w, (cluster['y']*weights).sum()/total_w
        else: new_x, new_y = cluster['x'].mean(), cluster['y'].mean()
        consolidated.append({'x': new_x, 'y': new_y, 'amplitude': seed['amplitude']})
        pending = pending[~(dists < min_dist)]
    return pd.DataFrame(consolidated)

def process_single_frame(frame, diameter, threshold, min_dist, noise_size=3.0):
    search_dia = max(15, diameter)
    if search_dia % 2 == 0: search_dia += 1
    
    processed_frame = tp.bandpass(frame, noise_size, 101, threshold=0)
    candidates = tp.locate(processed_frame, diameter=search_dia, minmass=threshold*100)
    if len(candidates) == 0: return pd.DataFrame(), pd.DataFrame(), processed_frame

    refined_pos = []
    for _, row in candidates.iterrows():
        fit = fit_spot_position_strict(frame, row['x'], row['y'], radius=int(diameter/2)+5)
        if fit: 
            refined_pos.append(fit)
        else:
            # Fallback Position
            refined_pos.append({'x': row['x'], 'y': row['y'], 'amplitude': frame[int(row['y']), int(row['x'])]})
    
    if not refined_pos: return candidates, pd.DataFrame(), processed_frame
    
    df_merged = aggregate_simple(pd.DataFrame(refined_pos), min_dist=min_dist)
    
    # Radius Messung mit Validierungs-Check
    real_radii = []
    fit_status = [] # Neue Liste für True/False
    
    for _, row in df_merged.iterrows():
        r_px, success = measure_radius_at_fixed_pos(frame, row['x'], row['y'], guess_diameter=diameter)
        real_radii.append(r_px)
        fit_status.append(success)
    
    df_merged['real_size'] = real_radii
    df_merged['valid_fit'] = fit_status # Speichern in DataFrame
    
    return candidates, df_merged, processed_frame