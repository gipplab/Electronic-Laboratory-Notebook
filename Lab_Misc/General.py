import glob, os
import datetime
from Exp_Main.models import ExpBase, ExpPath
from Exp_Sub.models import ExpBase as ExpBase_Sub
from Exp_Sub.models import ExpPath as ExpPath_Sub
from django.apps import apps


cwd = os.getcwd()
if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
    BaseFolderName = '01_Experimental'
else:
    BaseFolderName = '01_Data'

OS_BasePath = 'Add Basepart of your local device'
def get_BasePath():
    if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
        return cwd[0:cwd.find('01_Experimental')]
    else:
        path = os.path.join(cwd, BaseFolderName)
        if os.path.exists(path):
            return '/code'
        else:
            print('Basepath not found restart program.')


def get_DatesInFolder():
    all_dates =[]
    for date in glob.glob("*/"):
        try:
            is_date = datetime.datetime.strptime(date[0:-1], '%Y%m%d')
            all_dates.append(date)
        except:
            pass
    return all_dates

def is_linux():
    if os.name == 'posix':
        return True
    else:
        return False

def get_smart_time(time_seconds):
    """
    Wandelt Sekunden in eine sinnvolle Einheit um (s, min, h).
    Gibt (skalierte_zeiten, einheit) zurück.
    Funktioniert für einzelne Zahlen oder Pandas-Serien.
    """
    import numpy as np
    
    # Bestimme das Maximum, um die Einheit zu wählen
    max_t = np.max(time_seconds)
    
    if max_t > 7200:      # > 2 Stunden
        return time_seconds / 3600.0, "h"
    elif max_t > 120:     # > 2 Minuten
        return time_seconds / 60.0, "min"
    else:                 # Standard: Sekunden
        return time_seconds, "s"

def is_AppendableTime(file_name):
    try:
        is_date = datetime.datetime.strptime(file_name[0:6], '%H%M%S')
        return True
    except:
        return False

def save_index(array, item):
    try:
        index = array.index(item)
    except:
        index = -1
    return index

def get_LastIndex(list, searched):
    indices = [i for i, x in enumerate(list) if x == searched]
    return indices[-1]

def get_ModelOrigin(ModelName):
    try:
        ExpPath.objects.get(Abbrev = ModelName)
        return 'Exp_Main'
    except:
        try:
            ExpPath_Sub.objects.get(Abbrev = ModelName)
            return 'Exp_Sub'
        except:
            return None


def get_in_full_model(Main_id):
    curr_entry = ExpBase.objects.get(pk = Main_id)
    curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
    curr_model = apps.get_model('Exp_Main', str(curr_exp.Abbrev))
    entry = curr_model.objects.get(pk = Main_id)
    return entry

def get_in_full_model_sub(Main_id):
    curr_entry = ExpBase_Sub.objects.get(pk = Main_id)
    curr_exp = ExpPath_Sub.objects.get(Name = str(curr_entry.Device))
    curr_model = apps.get_model('Exp_Sub', str(curr_exp.Abbrev))
    entry = curr_model.objects.get(pk = Main_id)
    return entry

def get_FloatAfterTrigger(string, trigger):
    """Allows to retrive number after keyword ignors first blank.
    e.g. sting = blax 4,3sdflk would return 4.3
    """
    def conv(x):
        return x.replace(',', '.').encode()
    Float = None
    if string.find(trigger)!=-1:
        if trigger == 'y':
            ind = get_LastIndex(string, trigger)
        else:
            ind = string.index(trigger)
        for i in range(8):
            try:
                Float = float(conv(string[ind+1:ind+2+i]))
            except:
                if i == 0:
                    pass
                else:
                    break
    return Float

import pandas as pd
import numpy as np

def process_mfp_tracks(tracks, dash_exp, best_rad_col, img_w, img_h, default_cutoff=40.0):
    """
    Bereinigt, taggt und berechnet die Kinematik der MFP-Tracks für das Dashboard.
    """
    tracks['particle'] = tracks['particle'].astype(str)
    tracks['status'] = 'Valid'

    # 1. Connect IDs & Exclude IDs
    if dash_exp:
        if dash_exp.Connected_IDs:
            for pair in dash_exp.Connected_IDs.replace(',', ' ').split():
                if ':' in pair:
                    p1, p2 = [p.strip() for p in pair.split(':')]
                    tracks.loc[tracks['particle'].isin([p1, p2]), 'particle'] = f"{p1} C {p2}"
        if dash_exp.Excluded_IDs:
            exc_list = [str(x.strip()) for x in dash_exp.Excluded_IDs.replace(',', ' ').split() if x.strip()]
            tracks.loc[tracks['particle'].isin(exc_list), 'status'] = 'Ausgeschlossen (Manuell)'

    # 2. Radius Cut-off Tagging (Aussortieren falscher Größe)
    cutoff = float(dash_exp.Radius_Cutoff) if (dash_exp and dash_exp.Radius_Cutoff and float(dash_exp.Radius_Cutoff) > 0) else default_cutoff
    if cutoff > 0:
        tracks.loc[tracks[best_rad_col] < cutoff, 'status'] = f'Radius < Cut-off ({cutoff:.0f}px)'

    # 3. Randberührung (Exakt am Rand ohne Puffer)
    if 'x' in tracks.columns and 'y' in tracks.columns:
        touches_edge = (
            (tracks['x'] - tracks[best_rad_col] <= 0) | 
            (tracks['x'] + tracks[best_rad_col] >= img_w) | 
            (tracks['y'] - tracks[best_rad_col] <= 0) | 
            (tracks['y'] + tracks[best_rad_col] >= img_h)
        )
        edge_ids = tracks[touches_edge]['particle'].unique()
        tracks.loc[tracks['particle'].isin(edge_ids), 'status'] = 'Randberührung'

    # 4. Kinematik & Wachstum berechnen
    PIXEL_TO_UM = 0.064
    tracks['radius_um'] = tracks[best_rad_col] * PIXEL_TO_UM
    tracks['radius_smooth_um'] = tracks.groupby('particle')['radius_um'].transform(lambda x: x.rolling(window=3, center=True, min_periods=1).mean())
    tracks['delta_r_um'] = tracks.groupby('particle')['radius_smooth_um'].diff().fillna(0)
    
    median_delta = tracks.groupby('frame')['delta_r_um'].median().reset_index().rename(columns={'delta_r_um': 'median_delta_r_um'})
    tracks = tracks.merge(median_delta, on='frame', how='left')
    tracks['norm_delta_r_um'] = (tracks['delta_r_um'] - tracks['median_delta_r_um']).fillna(0)
    tracks['cum_norm_growth_um'] = tracks.groupby('particle')['norm_delta_r_um'].cumsum()

    # 5. Intensitäten & Total Normalized Intensity berechnen
    tracks['area_px'] = (np.pi * (tracks[best_rad_col] ** 2)).replace(0, np.nan) 
    
    # Primär: Measure-Kanal (🔴)
    if 'intensity_measure' in tracks.columns:
        tracks['mean_intensity_measure'] = tracks['intensity_measure'] / tracks['area_px']
        tracks['total_intensity'] = tracks['intensity_measure'] * tracks['area_px']
        first_area = tracks.groupby('particle')['area_px'].transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else 1)
        tracks['norm_total_intensity'] = tracks['total_intensity'] / first_area

    # Sekundär/Fallback: Detect-Kanal (🟢)
    if 'intensity_detect' in tracks.columns:
        tracks['mean_intensity_detect'] = tracks['intensity_detect'] / tracks['area_px']
        # 🚨 FALLBACK: Wenn kein roter Kanal existiert, nutze den grünen für den Scatter Plot!
        if 'norm_total_intensity' not in tracks.columns:
            tracks['total_intensity'] = tracks['intensity_detect'] * tracks['area_px']
            first_area = tracks.groupby('particle')['area_px'].transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else 1)
            tracks['norm_total_intensity'] = tracks['total_intensity'] / first_area

    return tracks