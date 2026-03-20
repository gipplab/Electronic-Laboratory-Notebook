import glob, os
import pandas as pd
import numpy as np
import datetime
from django.apps import apps
from django.utils import timezone
from functools import reduce
from dbfread import DBF
import pickle
# Deine Projekt-Importe
from Exp_Main.models import OCA, ExpBase, ExpPath, RSD, DAF, SFG
from Analysis.models import OszAnalysis
from Analysis.models import DafAnalysis
from Exp_Sub.models import LSP, MFR, CAP
from Lab_Misc import General
import nd2

# --- OPTIONALER IMPORT FÜR DATATABLE ---
try:
    from datatable import (dt, fread, f, by, ifelse, update, sort,
                           count, min, max, mean, sum, rowsum)
    HAS_DATATABLE = True
except ImportError:
    HAS_DATATABLE = False
    print("Info: 'datatable' library not found. Functions relying on it (Load_LMP_cosolvent) will return empty.")

cwd = os.getcwd()
rel_path = General.get_BasePath()

def Load_from_Model(ModelName, pk):
    # Dictionary Dispatcher statt langer If-Kette
    loaders = {
        'OCA': Load_OCA,
        'RSD': Load_RSD,
        'LSP': Load_LSP,
        'MFL': Load_MFL,
        'MFR': Load_MFR,
        'HME': Load_HME,
        'SEL': Load_SEL,
        'TCM': Load_TCM,
        'HIA': Load_HIA,
        'DAF': Load_sliced_DAF,
        'CAP': Load_CAP,
        'SFG': Load_SFG,
        'GRV': GRV_diff,
        'MFP': Load_MFP,
        # 'DRP': Load_DRP 
    }
    
    if ModelName in loaders:
        return loaders[ModelName](pk)
    else:
        print(f"Warning: No loader found for Model {ModelName}")
        return None

def conv(x):
    return x.replace(',', '.').encode()

def Load_SFG(pk):
    entry = SFG.objects.get(id = pk)
    file = os.path.join( rel_path, entry.Link)
    try:
        if file.endswith('_data.txt'):
            data = np.genfromtxt((conv(x) for x in open(file)), delimiter=' ', skip_header=5, names=['Wellenzahl', 'smth_1', 'smth_2', 'Signal'])
        else:
            data = np.genfromtxt(file, delimiter=',', skip_header=0, names=['Wellenzahl', 'Signal'])
    except:
        # Update: on_bad_lines
        data = pd.read_csv(file, sep='  ', on_bad_lines='skip', engine='python')
        data.columns = ["Wellenzahl", "Signal"]
        data = data[pd.to_numeric(data.Wellenzahl, errors='coerce').notnull()]
    return data

# --- Imports sicherstellen ---
from django.apps import apps
from Lab_Misc import General
import os

# ... (Dein existierender Code) ...

def Load_MFP_Path(pk):
    """
    Lädt den Pfad zur .nd2 Datei rein über Django ORM.
    Nutzt den Parent-Child Trick (ExpBase -> mfp), um Verwechslungen auszuschließen.
    """
    link = None
    
    try:
        # STRATEGIE: Wir laden das Eltern-Objekt (ExpBase).
        # Das ist eindeutig und existiert nur einmal.
        ExpBase = apps.get_model('Exp_Main', 'ExpBase')
        base_obj = ExpBase.objects.get(id=pk)
        
        # Django verlinkt das Kind automatisch als Attribut (kleingeschrieben)
        # Das garantiert, dass wir das 'echte' MFP aus Exp_Main bekommen.
        if hasattr(base_obj, 'mfp'):
            link = base_obj.mfp.Link
        else:
            print(f"Warning: ID {pk} ist kein MFP Experiment.")
            
    except Exception as e:
        print(f"Error loading MFP Path via ORM: {e}")
        return None

    # Pfad prüfen und zurückgeben
    if link:
        full_path = os.path.join(General.get_BasePath(), link)
        if os.path.exists(full_path):
            return full_path
    
    return None

def Load_MFP_Video(pk):
    """
    Lädt das ND2-Video für eine MFP-Analyse-ID.
    Nutzt Load_MFP_Path() für höchste Sicherheit beim Pfad.
    Geht direkt von 4D-Daten (Time, Channel, Y, X) aus.
    """
    from Analysis.models import MFPAnalysis
    
    # 1. Pfad mit deiner extrem sicheren Funktion holen!
    source_file = Load_MFP_Path(pk)
    
    if not source_file:
        print(f"❌ Video-Datei für ID {pk} konnte nicht ermittelt werden.")
        return None
        
    # 2. Analyse-Objekt für die Kanal-Einstellungen holen
    try:
        analysis = MFPAnalysis.objects.get(Entry_id=pk)
        detect_ch = getattr(analysis, 'Detect_Channel', 0)
    except Exception as e:
        print(f"⚠️ Keine Analyse-Settings für ID {pk} gefunden, nutze Standard. ({e})")
        detect_ch = 0
        analysis = None
        
    measure_ch = 1 if detect_ch == 2 else 0 
    bf_ch = 0 # Brightfield ist Kanal 0
    
    # 3. ND2 Datei laden (ohne 5D-Z-Stack-Logik!)
    with nd2.ND2File(source_file) as f:
        arr = f.asarray()
        
        # Standard-Fall: 4D (Time, Channel, Y, X)
        if arr.ndim == 4: 
            vid_detect = arr[:, detect_ch, :, :]
            vid_measure = arr[:, measure_ch, :, :]
            vid_bf = arr[:, bf_ch, :, :]
        # Fallback
        else: 
            vid_detect = arr
            vid_measure = arr
            vid_bf = arr
            
    return {
        'detect': vid_detect,
        'measure': vid_measure,
        'brightfield': vid_bf,
        'path': source_file,
        'analysis_obj': analysis
    }

def Load_MFP(pk):
    """
    Lädt die Analyse-Ergebnisse (Tracks) eines MFP-Experiments.
    """
    # 1. Eintrag aus der Datenbank holen
    entry = General.get_in_full_model(pk) 
    
    # 2. Prüfen, ob eine Analyse existiert
    try:
        # KORREKTUR: Wir müssen das MFPAnalysis Model importieren und suchen
        from Analysis.models import MFPAnalysis
        
        # Suche nach Analyse, die zu diesem Experiment gehört (Entry_id = pk)
        analysis = MFPAnalysis.objects.get(Entry_id=pk)
        result_path = analysis.Result_Path
        
        if not result_path or not os.path.exists(result_path):
            print(f"Warning: No result path found for MFP ID {pk}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Warning: Could not access analysis for MFP ID {pk}: {e}")
        return pd.DataFrame()

    # 3. Pickle Datei laden
    try:
        with open(result_path, 'rb') as f:
            data_dict = pickle.load(f)
            
        tracks = data_dict.get('tracks', pd.DataFrame())
        
        if not tracks.empty:
            fps = getattr(entry, 'Frame_rate', 1.0) 
            if fps and fps > 0:
                tracks['time'] = tracks['frame'] / fps
            
            # WICHTIG: Pfad speichern, damit das Dashboard das Video findet
            if getattr(entry, 'Link', None):
                tracks['Source_File'] = entry.Link

        return tracks

    except Exception as e:
        print(f"Error loading pickle file for MFP ID {pk}: {e}")
        return pd.DataFrame()

def Load_LMP_cosolvent(pk, file_name):
    # CHECK OB DATATABLE VORHANDEN IST
    if not HAS_DATATABLE:
        print("Error: Cannot load LMP cosolvent data because 'datatable' is not installed.")
        return pd.DataFrame()

    entry = General.get_in_full_model(pk)
    file = os.path.join( rel_path, entry.Link)
    file = os.path.join(file, file_name)

    data_raw = fread(file)
    data_raw.names={'C0' : 'id_atom'}
    rename = {}
    for old_name, new_name in zip(data_raw.names[1:8], data_raw[8,3:].to_list()):
        rename[old_name] = new_name[0]

    data_raw.names=rename
    data_raw['times']=0
    cond = ifelse(f.type == 'TIMESTEP', f.times + 1,#set to one if timestep
                f.type == 'ITEM:', f.times + 2,#not used
                None)

    data_raw['case'] = data_raw[:, cond]
    data_raw['case'] = data_raw[:, dt.shift(f.case, n=1)]#shift to info row
    data_raw['time'] = ifelse(f.case == 1, f.id_atom, None)
    tine = data_raw['time'].to_pandas()
    data_raw['time'] = tine.ffill()#pull down times
    del data_raw[:, ['C8', 'C9', 'times', 'case']] 
    data_raw['type']=data_raw[:, dt.as_type(f.type, int)]#convert type
    data_raw['is_val'] = ifelse(f.type < 4, True, False)
    data = data_raw[(f.is_val==1), :]
    del data[:, ['is_val']]
    data[:,:] = dt.float32
    data['type']=data[:, dt.as_type(f.type, int)]
    data['time']=data[:, dt.as_type(f.time, int)]
    return data

def Load_SEL(pk):
    entry = General.get_in_full_model(pk)
    file = os.path.join( rel_path, entry.Link_XLSX)
    df = pd.read_excel(file)
    new_vals = df[df>1]/1000000 # correct for wrong format
    Curr_Dash = entry.Dash
    df.update(new_vals)
    df = df.rename(columns = {'Thickness # 3':'Thickness_Brush'})
    df = df.rename(columns = {'Thickness # 4':'Thickness_Brush'})
    df["Time (min.)"] = Curr_Dash.Start_datetime_elli + pd.TimedeltaIndex(df["Time (min.)"], unit='m')
    df["time"] = df["Time (min.)"].dt.tz_convert(timezone.get_current_timezone())
    df['time_loc'] = df["time"]
    return df

def GRV_diff(pk):
    entry = General.get_in_full_model(pk)
    # Sicherer Check auf Existenz
    if entry.Link_Data_processed:
        return Load_GRV_processed(pk)
    else:
        return Load_GRV(pk)

def Load_GRV_processed_side(pk):
    entry = General.get_in_full_model(pk)
    Folder = os.path.join( rel_path, entry.Link_Data_processed)
    os.chdir(Folder)
    try:
        df = pd.read_excel('Analysis_side.xlsx')
        df = df.rename(columns={"Type": "type", "Position": "position", "Value": "value", "Error": "error"})
        df.index = [df['type'], df['position']]
        scale = 1/148/2
        def conv_val(ss, val1, out):
            plate_w1 = (df.loc[ss,'height_beaker']['value']-df.loc[ss, val1]['value'])*scale
            df.loc[(ss,out), 'value'] = np.mean([plate_w1])

        conv_val('steady', 'height_ridge', 'height_ridge_diff')
        return df
    finally:
        os.chdir(cwd) # Immer zurücksetzen

def Load_GRV_processed(pk):
    entry = General.get_in_full_model(pk)
    Folder = os.path.join( rel_path, entry.Link_Data_processed)
    os.chdir(Folder)
    try:
        df = pd.read_excel('Analysis.xlsx')
        df = df.rename(columns={"Type": "type", "Position": "position", "Value": "value", "Error": "error"})
        df.index = [df['type'], df['position']]
        scale = df.loc['settings','scale']['value']
        def conv_val(ss, val1, val2, out):
            plate_w1 = (df.loc[ss,'beaker_hight']['value']-df.loc[ss, val1]['value'])*scale
            plate_w2 = (df.loc[ss,'beaker_hight']['value']-df.loc[ss, val2]['value'])*scale
            df.loc[(ss,out), 'value'] = np.mean([plate_w1, plate_w2])

        conv_val('static', 'plate1_white', 'plate2_white','white_upper_on_plate')
        conv_val('steady', 'plate1_white', 'plate2_white','white_upper_on_plate')
        conv_val('static', 'plate1', 'plate2','upper_on_plate')
        conv_val('steady', 'plate1', 'plate2','upper_on_plate')
        conv_val('static', 'ridge_c_1_white', 'ridge_c_2_white','white_upper_on_hill')
        conv_val('steady', 'ridge_c_1_white', 'ridge_c_2_white','white_upper_on_hill')
        conv_val('static', 'ridge_c_1', 'ridge_c_2','upper_on_hill')
        conv_val('steady', 'ridge_c_1', 'ridge_c_2','upper_on_hill')
        conv_val('static', 'ridge_e_1', 'ridge_e_2','on_hill_edge')
        conv_val('steady', 'ridge_e_1', 'ridge_e_2','on_hill_edge')
        return df
    finally:
        os.chdir(cwd)

def Load_GRV(pk):
    entry = General.get_in_full_model(pk)
    Folder = os.path.join( rel_path, entry.Link_Data)
    os.chdir(Folder)
    
    try:
        filenames= os.listdir (".") 
        result = []
        for filename in filenames: 
            if os.path.isdir(os.path.join(os.path.abspath("."), filename)): 
                result.append(filename)
        
        # Sicherer Index-Zugriff
        if len(result) > 1:
            os.chdir(result[1])
            offset = np.genfromtxt('offset.txt', delimiter=';')
            off = pd.DataFrame(offset.astype('int64'))
            os.chdir('..')
        else:
            off = pd.DataFrame()

        settings = pd.read_excel('settings.xlsx')
        saved_setting = settings
        saved_setting = saved_setting.set_index('Unnamed: 0')
        saved_setting = saved_setting.to_dict(orient = 'dict')
        saved_setting = saved_setting[0]
        settings = {**settings, **saved_setting}

        # Sicherer Zugriff auf settings und leere dfs
        if settings.get('Flipped_fit'):
            data_off = off[[0,2]] if not off.empty else pd.DataFrame()
            if not data_off.empty: data_off.columns = ['frame', 'shift_motor']
        else:
            data_off = off[[0,1]] if not off.empty else pd.DataFrame()
            if not data_off.empty: data_off.columns = ['frame', 'shift_motor']

        try:
            angle = entry.Dipping_angle
            scaling = np.sin(angle/180*np.pi)
            Bulk = entry.Pix_Pos_0
            conv_px_mm = entry.px_to_mm
            conversion_values = True
        except:
            conversion_values = False
            print('Conversion values are missing')

        data = {}
        for file in glob.glob('Analysis*.xlsx'):
            name = file[file.find('_')+1:file.find('.')]
            data[name] = pd.read_excel(file)
            if not data_off.empty:
                data[name] = pd.merge_asof(data[name], data_off.sort_values('frame'), on = 'frame')
            fps = entry.Frame_rate
            data[name]['time'] = data[name]['frame']/fps
            if conversion_values:
                data[name]['Height_over_Bulk'] = Bulk*conv_px_mm-(data[name]['transition']*scaling + off[[1]].min().item())*conv_px_mm
        
        if data:
            df = pd.concat(data.values(), keys=data.keys(), axis = 1)
        else:
            df = pd.DataFrame()
        return df
    finally:
        os.chdir(cwd)

def Load_TCM(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    df = pd.read_excel(file)   
    df["time_loc"] = df["time"].dt.tz_localize(timezone.get_current_timezone()) 
    return df

def Load_HIA(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    # Update: on_bad_lines
    df = pd.read_csv(file, sep=';', on_bad_lines='skip', decimal = '.')  
    df["time"] = pd.to_datetime(df['Time:'], errors='coerce')
    df["time_loc"] = df["time"].dt.tz_localize(timezone.get_current_timezone()) 
    return df

def get_subs_in_dic(pk):
    main_entry = General.get_in_full_model(pk)
    Sub_Exps = main_entry.Sub_Exp.all()
    data = {}
    for Sub_Exp in Sub_Exps:
        Sub_Exp = General.get_in_full_model_sub(Sub_Exp.pk)
        data_sub = Load_from_Model(Sub_Exp.Device.Abbrev, Sub_Exp.id)
        try:
            name = Sub_Exp.Name + '_' + Sub_Exp.Gas.first().Name
            data[name] = data_sub
        except:
            data[Sub_Exp.Name] = data_sub
    return data

def get_subs_by_model(pk, sub_model):
    main_entry = General.get_in_full_model(pk)
    main_model = str.lower(main_entry.Device.Abbrev)
    model = apps.get_model('Exp_Sub', sub_model)
    data = {}
    mfrs = model.objects.filter(**{main_model: ExpBase.objects.get(id = pk)}).all()
    for mfr in mfrs:
        try:
            name = mfr.Name + '_' + mfr.Gas.first().Name
            data[name] = Load_from_Model(mfr.Device.Abbrev, mfr.id)
        except:
            data[mfr.Name] = Load_from_Model(mfr.Device.Abbrev, mfr.id)
    return data

def Load_RSD_subs(pk):
    Gases = {}
    mfrs = MFR.objects.filter(rsd = ExpBase.objects.get(id = pk)).all()
    for mfr in mfrs:
        Gases[mfr.Gas.first().Name] = Load_MFR(mfr.id)

    Pump = {}
    lsps = LSP.objects.filter(rsd = ExpBase.objects.get(id = pk)).all()
    for lsp in lsps:
        Pump[lsp.Name] = Load_LSP(lsp.id)

    if len(Gases)>0:
        Gases = pd.concat(Gases)
    if len(Pump)>0:
        Pump = pd.concat(Pump)

    return Gases, Pump

def Load_RSD(pk):
    cwd = os.getcwd()
    entry = General.get_in_full_model(pk)
    os.chdir(os.path.join(General.get_BasePath(),entry.Link_Data))
    Drops = {}
    Drops_names = []
    # Sicherstellen, dass wir wieder zurückkommen
    try:
        for file in glob.glob("*.xlsx"):
            if file.startswith('Drop'):
                Drops[file[:-5]] = pd.read_excel(file)
                Drops_names.append(file[:-5])
    finally:
        os.chdir(cwd)
        
    if Drops:
        dropss = pd.concat(Drops, keys=Drops_names)
        dropss['time_loc'] = dropss['abs_time'].dt.tz_localize(timezone.get_current_timezone())
        return dropss
    return pd.DataFrame()

def Load_sliced_RSD(Main_id):
    data = Load_RSD(Main_id)
    entry = General.get_in_full_model(Main_id)
    DashTab = entry.Dash
    return Slice_data(data, DashTab)

def Load_MFL(pk):
    entry = General.get_in_full_model_sub(pk)
    MFL_N2_data = Load_csv(entry)
    MFL_N2_data['Date_Time'] = pd.to_datetime(MFL_N2_data['Date_Time'], format='%d.%m.%Y %H:%M:%S', errors="coerce")
    MFL_N2_data['time'] = MFL_N2_data['Date_Time'].dt.tz_localize(timezone.get_current_timezone())
    MFL_N2_data['time_loc'] = MFL_N2_data['time']
    return MFL_N2_data

def Load_MFR(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    # Update: on_bad_lines
    data = pd.read_csv(file, sep=' ', on_bad_lines='skip')
    data['date_time'] = pd.to_datetime(data['date'] + '_' + data['time'], format='%Y-%m-%d_%H:%M:%S.%f', errors="coerce")
    data['time_loc'] = data['date_time'].dt.tz_localize(timezone.get_current_timezone())
    return data

def Load_csv(entry):
    file = os.path.join( rel_path, entry.Link)
    # Update: on_bad_lines
    df = pd.read_csv(file, sep=';', on_bad_lines='skip', decimal = ',', parse_dates=[['Date', 'Time']])
    return df

def Load_HME(pk):
    entry = General.get_in_full_model_sub(pk)
    Humidity_data = Load_dfb(entry)
    Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
    Humidity_data['time'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
    try:
        col_RH = [x for x in Humidity_data.columns.values if "CHN1" in x]
        Humidity_data['Humidity'] = Humidity_data[col_RH]
    except:
        pass
    try:
        col_temp = [x for x in Humidity_data.columns.values if "CHN2" in x]
        Humidity_data['Temperature'] = Humidity_data[col_temp]
    except:
        pass
    Humidity_data['time_loc'] = Humidity_data['time']
    return Humidity_data

def Load_dfb(entry):
    file = os.path.join( rel_path, entry.Link)
    table = DBF(file, load=True)
    df = pd.DataFrame(iter(table))
    return df

def Load_OCA(Main_id):
    entry = OCA.objects.get(id = Main_id)
    file = os.path.join( rel_path, entry.Link_Data)
    tmp_dt = pd.read_table(file, sep='  ', decimal = ',', skiprows = 10, encoding= 'unicode_escape')
    if len(tmp_dt.columns) == 13:
        names = ['Run_No', 'Age', 'CA_M', 'CA_L', 'CA_R', 'CM', 'BD', 'Vol', 'Mag', 'a', 'b', 'c', 'd']
    else:
        names = ['Run_No', 'Age', 'CA_M', 'CA_L', 'CA_R', 'CM', 'BD', 'Vol', 'Mag', 'BI_left', 'BI_right', 'Height']
    data = pd.read_table(file, sep='    ', decimal = ',', names = names, skiprows = 10, encoding= 'unicode_escape')
    data['Age'] = data['Age']/1000
    slice_CA_high = (data['CA_L']<1800) & (data['CA_R']<1800)
    data = data[slice_CA_high]
    os.chdir(cwd)
    return data

def Load_DAF(Main_id):
    entry = DAF.objects.get(id = Main_id)
    try:
        file = os.path.join(rel_path, entry.Link_Data)
        data = pd.read_excel(file, header=0, index_col=0)
        info = pd.read_excel(file, sheet_name='Datacard', index_col=0)

        # Helper function for merging logic to reduce duplication
        def merge_extra(main_df, file_path, keep_cols, drop_cols_from_main):
            try:
                tmp_data = pd.read_excel(file_path, header=0)
                # Filter keep_cols to only those existing
                existing_cols = [c for c in keep_cols if c in tmp_data.columns]
                tmp_data = tmp_data[existing_cols]
                
                # Drop from main if exists
                drop_existing = [c for c in drop_cols_from_main if c in main_df.columns]
                main_df = main_df.drop(drop_existing, axis=1)
                
                return pd.merge(main_df, tmp_data, on=['framenumber'], how='outer')
            except:
                return main_df

        # Left Drop
        data = merge_extra(data, os.path.join(rel_path, entry.Link_Additional_Data_CAL),
                           ['framenumber', 'CA_L', 'contactpointleft', 'leftcontact_y', 'BI_left'],
                           ['CA_L', 'contactpointleft', 'leftcontact_y', 'BI_left'])

        # Right Drop
        data = merge_extra(data, os.path.join(rel_path, entry.Link_Additional_Data_CAR),
                           ['framenumber', 'CA_R', 'contactpointright', 'rightcontact_y', 'BI_right'],
                           ['CA_R', 'contactpointright', 'rightcontact_y', 'BI_right'])
        
        # 2nd Camera (Logic slightly more complex, keeping manual)
        try:
            file_2nd = os.path.join(rel_path, entry.Link_Data_2nd_Camera)
            tmp_data = pd.read_excel(file_2nd, header=0)
            if 'width / mm' in tmp_data.columns:
                tmp_data = tmp_data[['framenumber', 'width', 'width / mm']]
            elif 'width' in tmp_data.columns:
                tmp_data = tmp_data[['framenumber', 'width']]
            elif 'BI_left' in tmp_data.columns:
                tmp_data['width / mm'] = tmp_data['contactpointright'] - tmp_data['contactpointleft']
                tmp_data['width'] = tmp_data['BI_right'] - tmp_data['BI_left']
                tmp_data = tmp_data[['framenumber', 'width', 'width / mm']]
            else:
                tmp_data['width'] = tmp_data['BI_right'] - tmp_data['BI_left']
                tmp_data = tmp_data[['framenumber', 'width']]
            data = pd.merge(data, tmp_data, on=['framenumber'], how='outer')
        except:
            pass

        data['time_loc'] = data['abs_time'].dt.tz_localize(timezone.get_current_timezone())
        data['Age'] = (pd.to_datetime(data['time_loc']) - pd.to_datetime(data['time_loc'].to_numpy()[0])).dt.total_seconds()
        cap_entry = CAP.objects.get(Capillary = entry.Capillary)
        effective_spring_const = cap_entry.Spring_Constant_N_per_m * cap_entry.Effective_Length_mm/(cap_entry.Effective_Length_mm - info["value"]["needle_offset"]*info["value"]["pix_calibration"])
        data['force / mN'] = data['deflection / mm'] * effective_spring_const

    except Exception as e:
        print(f"No data file existing for {entry.Name} or Error: {e}")
        data = pd.DataFrame()
    
    return data

def Load_CAP(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link_Data)
    data = pd.read_csv(file, skiprows=3, header=None, names=["label", "framenumber", "position"])
    data = data.sort_values(by=["framenumber"]) 
    data["time"] = data["framenumber"] / entry.FPS
    return data

def Load_sliced_OCA(Main_id):
    data = Load_OCA(Main_id)
    entry = General.get_in_full_model(Main_id)
    DashTab = entry.Dash
    return Slice_data(data, DashTab)

def Load_sliced_DAF(Main_id):
    data = Load_DAF(Main_id)
    entry = General.get_in_full_model(Main_id)
    DashTab = entry.Dash
    return Slice_data(data, DashTab)

def Slice_data(data, DashTab):
    if data.empty: return data

    if isinstance(DashTab.CA_high_degree, float):
        data = data[(data['CA_L']<DashTab.CA_high_degree) & (data['CA_R']<DashTab.CA_high_degree)]

    if isinstance(DashTab.CA_low_degree, float):
        data = data[(data['CA_L']>DashTab.CA_low_degree) & (data['CA_R']>DashTab.CA_low_degree)]

    if isinstance(DashTab.BD_high_mm, float):
        data = data[(data['BI_left']<DashTab.BD_high_mm) & (data['BI_right']<DashTab.BD_high_mm)]

    if isinstance(DashTab.BD_low_mm, float):
        data = data[(data['BI_left']>DashTab.BD_low_mm) & (data['BI_right']>DashTab.BD_low_mm)]

    if isinstance(DashTab.Time_high_sec, float):
        data = data[data['Age']<DashTab.Time_high_sec]

    if isinstance(DashTab.Time_low_sec, float):
        data = data[data['Age']>DashTab.Time_low_sec]
        
    try:
        if isinstance(DashTab.Width_high_mm, float):
            data = data[data['width / mm']<DashTab.Width_high_mm]

        if isinstance(DashTab.Width_low_mm, float):
            data = data[data['width / mm']>DashTab.Width_low_mm]

        if isinstance(DashTab.Force_high_muN, float):
            data = data[data['force / mN']<1000*DashTab.Force_high_muN]

        if isinstance(DashTab.Force_low_muN, float):
            data = data[data['force / mN']>1000*DashTab.Force_low_muN]
    except:
        pass

    return data


def Load_sub_LSP(Main_id):
    entry = General.get_in_full_model(Main_id)
    indices = [str(s) for i, s in enumerate(list(entry.Sub_Exp.all())) if 'LSP' in str(s)]

    if len(indices)==2:
        df = Load_LSP(LSP.objects.get(Name = indices[0]))
        df2 = Load_LSP(LSP.objects.get(Name = indices[1]))
        df['Current flow rate'] = df['Current flow rate']+df2['Current flow rate']
        print('Create new effective flowrate!')
    elif len(indices) == 1:
        df = Load_LSP(LSP.objects.get(Name = indices[0]))
    else:
        print('Wrong amount of LSPs!')
        return pd.DataFrame()
        
    DashTab = entry.Dash
    time_to_add = DashTab.Time_diff_pump if isinstance(DashTab.Time_diff_pump, float) else 0
    df['Age_s'] = df['Age_s'] + time_to_add
    return df

def Load_LSP(sub_id):
    Syringe_pump = LSP.objects.get(pk = sub_id)
    file = os.path.join( rel_path, Syringe_pump.Link)
    df = pd.read_excel(file, 'Events record')
    temp_time = pd.to_datetime(df['Current time'])
    time_diff = Syringe_pump.Date_time.date()-temp_time[0].date()
    df['date_time'] = temp_time + time_diff
    index_change_time = np.argmin(temp_time-temp_time[0])
    if not index_change_time == 0:
        df['date_time'][index_change_time:] = df['date_time'][index_change_time:] + datetime.timedelta(days=1)
    df['time_loc'] = df['date_time'].dt.tz_localize(timezone.get_current_timezone())
    df['Age_dt'] = pd.to_datetime(df["Event time"], format='%H:%M:%S,%f').dt.time
    df['Age_s'] = [time.hour*60*60+time.minute*60+time.second+time.microsecond/1000000 for time in df['Age_dt']]
    return df

def Load_OszAnalysis_in_df(Osz_Ana_id):
    # UPDATE: Optimiert - Sammeln in Listen statt append, dann einmaliges concat
    entry = OszAnalysis.objects.get(id = Osz_Ana_id)
    OszBaseParam_inst = entry.OszBaseParam.all()
    
    # Listen für Daten
    rows_left = []
    rows_right = []
    rows_drop_nr = []

    for item in OszBaseParam_inst:
        row = {'Max_CL': item.Max_CL, 'Max_CA': item.Max_CA, 'Min_CA': item.Min_CA, 'Min_AdvCA': item.Min_AdvCA}
        if item.LoR_CL == 'Left':
            rows_left.append(row)
            rows_drop_nr.append({'Drop_Nr': item.Drop_Nr})
        elif item.LoR_CL == 'Right':
            rows_right.append(row)
            
    cols = ['Max_CL', 'Max_CA', 'Min_CA', 'Min_AdvCA']
    df_ana_res_left = pd.DataFrame(rows_left) if rows_left else pd.DataFrame(columns=cols)
    df_ana_res_right = pd.DataFrame(rows_right) if rows_right else pd.DataFrame(columns=cols)
    Drop_parameters = pd.DataFrame(rows_drop_nr) if rows_drop_nr else pd.DataFrame(columns=['Drop_Nr'])
    
    df_drop_pram = pd.concat([Drop_parameters, df_ana_res_left, df_ana_res_right], keys=['General', 'Left', 'Right'], axis = 1)

    # Fit Results
    OszFitRes_inst = entry.OszFitRes.all()
    fit_left_val, fit_left_err = [], []
    fit_right_val, fit_right_err = [], []
    drop_nrs = []
    
    for item in OszFitRes_inst:
        row = {'x_pos': item.x_pos, 'y_pos': item.y_pos, 'Step_width': item.Step_width, 'Step_hight': item.Step_hight}
        if item.LoR_CL == 'Left':
            if item.ErroVal == 'Value':
                fit_left_val.append(row)
                drop_nrs.append(item.Drop_Nr)
            elif item.ErroVal == 'Error':
                fit_left_err.append(row)
        elif item.LoR_CL == 'Right':
            if item.ErroVal == 'Value':
                fit_right_val.append(row)
            elif item.ErroVal == 'Error':
                fit_right_err.append(row)

    cols_fit = ['x_pos', 'y_pos', 'Step_width', 'Step_hight']
    
    def mk_df(data): return pd.DataFrame(data) if data else pd.DataFrame(columns=cols_fit)

    df_fit_res_left = pd.concat([mk_df(fit_left_val), mk_df(fit_left_err)], keys=['Value', 'Error'], axis=1)
    df_fit_res_right = pd.concat([mk_df(fit_right_val), mk_df(fit_right_err)], keys=['Value', 'Error'], axis=1)
    df_fit_res = pd.concat([df_fit_res_left, df_fit_res_right], keys=['Left', 'Right'], axis=1)
    
    # Multiindex DropNr manuell hinzufügen
    df_drop_nr_col = pd.DataFrame(drop_nrs, columns=['Drop_Nr'])
    if not df_drop_nr_col.empty:
        df_drop_nr_col.columns = pd.MultiIndex.from_tuples([('General', 'General', 'Drop_Nr')])
    else:
         df_drop_nr_col = pd.DataFrame(columns=pd.MultiIndex.from_tuples([('General', 'General', 'Drop_Nr')]))
         
    df_fit_res = pd.concat([df_drop_nr_col, df_fit_res], axis=1)


    # Derived Results
    OszDerivedRes_inst = entry.OszDerivedRes.all()
    der_left, der_right, der_drop = [], [], []

    for item in OszDerivedRes_inst:
        row = {'Hit_prec': item.Hit_prec, 'Fit_score': item.Fit_score}
        if item.LoR_CL == 'Left':
            der_left.append(row)
            der_drop.append({'Drop_Nr': item.Drop_Nr})
        elif item.LoR_CL == 'Right':
            der_right.append(row)

    cols_der = ['Hit_prec', 'Fit_score']
    df_OszDerivedRes_left = pd.DataFrame(der_left) if der_left else pd.DataFrame(columns=cols_der)
    df_OszDerivedRes_right = pd.DataFrame(der_right) if der_right else pd.DataFrame(columns=cols_der)
    df_der_drop = pd.DataFrame(der_drop) if der_drop else pd.DataFrame(columns=['Drop_Nr'])

    df_OszDerivedRes = pd.concat([df_der_drop, df_OszDerivedRes_left, df_OszDerivedRes_right], keys=['General', 'Left', 'Right'], axis = 1)
    return df_drop_pram, df_fit_res, df_OszDerivedRes

def Load_DAFAnalysis_in_df(DAF_id):
    Exp = DAF.objects.get(id = DAF_id)
    try:
        data_path = os.path.join(General.get_BasePath(), Exp.Link_Result)
        df = pd.read_excel(data_path, header=0, index_col=0)
        columns = df.columns.values
        df_np = df.to_numpy()
        data = pd.DataFrame([df_np[-2]], columns=columns)
        errors = pd.DataFrame([df_np[-1]], columns=columns)
    except:
        print("No analysis results existing for ", Exp.Name)
        data, errors = pd.DataFrame(), pd.DataFrame()
    
    return data, errors