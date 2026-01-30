import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from Analysis.models import LMPCosolventAnalysis
from Exp_Main.models import ExpBase, LMP
from Lab_Misc import Load_Data

# --- OPTIONALER IMPORT: DATATABLE ---
# Wird für Performance bei großen Dateien zwingend benötigt.
try:
    from datatable import (dt, fread, f, by, ifelse, update, sort,
                           count, min, max, mean, sum, rowsum)
    HAS_DATATABLE = True
except ImportError:
    HAS_DATATABLE = False
    # Dummies, damit der Interpreter bei Funktionsdefinitionen nicht meckert
    dt = f = None
    print("Warnung: 'datatable' nicht gefunden. Analysen für LMP Cosolvent werden übersprungen.")

def ana_lmp_cosolvent(pk):
    # 1. Check: Ist datatable installiert?
    if not HAS_DATATABLE:
        print(f"Abbruch für Experiment {pk}: 'datatable' fehlt (Performance-kritisch).")
        return

    # 2. Daten laden (Erwartet datatable Frame aus Load_Data)
    data = Load_Data.Load_LMP_cosolvent(pk, 'polymer_cosolvent.out')
    
    # Check ob Daten geladen wurden (Load_Data könnte leeren DF zurückgeben)
    if data is None or (hasattr(data, 'nrows') and data.nrows == 0):
        print(f"Keine Daten für {pk} geladen.")
        return

    # Ab hier: Originale, schnelle datatable-Logik
    times = dt.unique(data['time']).sort('time')
    last_time = times[-1, :]

    base_exp = ExpBase.objects.get(id = pk)
    anz_part = []
    dfs = {}
    
    # Variablen initialisieren um 'UnboundLocalError' zu vermeiden
    height = 0 

    for i in [1,2,3]:
        # Filter: Type == i UND Time == letzter Zeitschritt
        # f.z selektiert die Z-Spalte
        selection = data[((f.type == i ) & (f.time == last_time)), f.z]
        points = selection
        
        if i == 1:
            # Berechnung der Höhe (Mean * 2)
            # .to_list()[0][0] extrahiert den Wert aus dem 1x1 Resultat
            mean_val = points.mean().to_list()[0][0]
            if mean_val is None: mean_val = 0
            height = mean_val * 2
            
            # Spezialfall für Experiment Typ 21
            if len(base_exp.Type.filter(id = 21)) == 1:
                data2 = data[(f.type == 1), :]
                # Gruppieren nach Zeit, Mittelwert von Z berechnen
                data2 = data2[:, mean(f.z), by(f.time)]
                # Die letzten 50 Zeitschritte ignorieren ([:-50])
                if data2.nrows > 50:
                    val = data2[:-50, mean(f.z)].mean().to_list()[0][0]
                    if val is not None: height = val * 2

        # Histogramm mit Numpy/Matplotlib (Umwandlung zu Numpy Array passiert implizit)
        points_np = np.array(points).flatten()
        counts, bins, bars = plt.hist(points_np, 200)
        plt.close() # Wichtig: Speicher freigeben!

        len_points = points.nrows
        data_dic = {'counts': counts, 'bins': bins[:-1]}
        df = pd.DataFrame(data=data_dic)
        
        anz_part.append(len_points)
        dfs[i] = df

    # Speichern
    directory = os.path.join('Private', '02_Dataframes', 'LMP_Cosolvent_Analysis', 'LCA_' + base_exp.Name)
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    dfs[1].to_csv(os.path.join(directory, 'Hist_Mono.csv'))
    dfs[2].to_csv(os.path.join(directory, 'Hist_H2O.csv'))
    dfs[3].to_csv(os.path.join(directory, 'Hist_EtOH.csv'))
    
    item = LMP.objects.get(id = pk) 
    item.lmpcosolventanalysis_set.all().delete()
    
    # Safe Index Access für anz_part
    anz_etoh = anz_part[1] if len(anz_part) > 1 else 0
    anz_h2o = anz_part[2] if len(anz_part) > 2 else 0

    entry = LMPCosolventAnalysis(Name = 'LCA_' + base_exp.Name, 
                                 Anz_H2O = anz_h2o, 
                                 Anz_EtOH = anz_etoh, 
                                 Height = height, 
                                 Link_Hist_Mono = os.path.join(directory, 'Hist_Mono.csv'), 
                                 Link_Hist_H2O = os.path.join(directory, 'Hist_H2O.csv'), 
                                 Link_Hist_EtOH = os.path.join(directory, 'Hist_EtOH.csv'),
                                 Exp = base_exp)
    entry.save()
    
    # Speicher explizit freigeben (wichtig bei großen datatables)
    del data

def ana_lmp_cosolvent_err(pk, times_back = 100):
    if not HAS_DATATABLE:
        return

    data = Load_Data.Load_LMP_cosolvent(pk, 'polymer_cosolvent.out')
    
    if data is None or (hasattr(data, 'nrows') and data.nrows == 0):
        return

    times = dt.unique(data['time']).sort('time')
    
    # Zeitgrenze bestimmen
    # times ist ein Frame (n x 1), Zugriff via slice oder to_list
    n_times = times.nrows
    if n_times > times_back:
        # Zugriff auf den Wert beim Index -times_back
        limit_val = times[n_times - times_back, 0]
    else:
        limit_val = times[0, 0]

    base_exp = ExpBase.objects.get(id = pk)
    anz_part = []
    dfs = {}
    
    height = 0
    height_err = 0

    for i in [1,2,3]:
        # Filterung: Type == i UND Time > limit_val
        filter_cond = (f.type == i) & (f.time > limit_val)
        d_z = data[filter_cond, :]

        if d_z.nrows == 0:
            df = pd.DataFrame([[0,0,0]], columns=['Position', '#_counts', 'Error'])
            dfs[i] = df
            anz_part.append(0)
            continue

        # Daten für Histogramm extrahieren
        z_positions = d_z[:, f.z].to_numpy().flatten()
        time_steps = d_z[:, f.time].to_numpy().flatten()
        
        i_z_max = int(d_z[:, f.z].max()[0,0])

        bins = np.arange(0, i_z_max+3, 1)
        
        # Vektorisierte Berechnung der Histogramme pro Zeitschritt
        # (Vermeidet langsame Python Loops über Frames)
        unique_t = np.unique(time_steps)
        histograms = []
        for t in unique_t:
            hist, _ = np.histogram(z_positions[time_steps == t], bins=bins)
            histograms.append(hist)
        histograms = np.array(histograms)

        mean_histogram = histograms.mean(axis=0)
        std_histogram = histograms.std(axis=0)

        positions = np.linspace(0.5, i_z_max+1.5, i_z_max+1) # angepasst auf bin-Länge
        
        # Dimensions-Check (falls Rundungsfehler bei int(max))
        min_len = min(len(positions), len(mean_histogram))
        positions = positions[:min_len]
        counts = mean_histogram[:min_len]
        errors = std_histogram[:min_len]

        # Schwerpunktberechnung
        sum_counts = np.sum(counts)
        if sum_counts > 0:
            center_of_mass = np.sum(positions * counts) / sum_counts
            weighted_positions = positions * counts
            # Fehlerfortpflanzung
            error_center_of_mass = np.sqrt(np.sum((positions * errors / sum_counts)**2))
        else:
            center_of_mass = 0
            error_center_of_mass = 0

        df = pd.DataFrame({
            'Position': positions,
            '#_counts': counts,
            'Error': errors
        })

        if i == 1:
            height = center_of_mass*2
            height_err = error_center_of_mass*2

        # Anzahl Partikel im allerletzten Zeitschritt für Statistik
        last_t_val = times[n_times-1, 0]
        points_last = data[((f.type == i ) & (f.time == last_t_val)), f.z]
        len_points = points_last.nrows
        anz_part.append(len_points)
        dfs[i] = df

    directory = os.path.join('Private', '02_Dataframes', 'LMP_Cosolvent_Analysis', 'LCA_' + base_exp.Name)
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    dfs[1].to_csv(os.path.join(directory, 'Hist_Mono_err.csv'))
    dfs[2].to_csv(os.path.join(directory, 'Hist_H2O_err.csv'))
    dfs[3].to_csv(os.path.join(directory, 'Hist_EtOH_err.csv'))
    
    item = LMP.objects.get(id = pk) 
    item.lmpcosolventanalysis_set.all().delete()
    
    anz_etoh = anz_part[1] if len(anz_part) > 1 else 0
    anz_h2o = anz_part[2] if len(anz_part) > 2 else 0

    entry = LMPCosolventAnalysis(Name = 'LCA_' + base_exp.Name, 
                                 Anz_H2O = anz_h2o, 
                                 Anz_EtOH = anz_etoh, 
                                 Height = height, 
                                 Height_Err = height_err, 
                                 Link_Hist_Mono = os.path.join(directory, 'Hist_Mono_err.csv'), 
                                 Link_Hist_H2O = os.path.join(directory, 'Hist_H2O_err.csv'), 
                                 Link_Hist_EtOH = os.path.join(directory, 'Hist_EtOH_err.csv'),
                                 Exp = base_exp)
    entry.save()
    del data