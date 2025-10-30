from datatable import (dt, fread, f, by, ifelse, update, sort,
                       count, min, max, mean, sum, rowsum)
import matplotlib.pyplot as plt
import pandas as pd
from Analysis.models import LMPCosolventAnalysis
from Exp_Main.models import ExpBase
import os 
import numpy as np
from Lab_Misc import Load_Data
from Exp_Main.models import LMP

def ana_lmp_cosolvent(pk):
    data = Load_Data.Load_LMP_cosolvent(pk, 'polymer_cosolvent.out')
    times = dt.unique(data['time']).sort('time')

    base_exp = ExpBase.objects.get(id = pk)
    anz_part = []
    dfs = {}
    for i in [1,2,3]:
        points = data[((f.type == i )& (f.time == times[-1, :])), f.z]
        if i == 1:
            height = points.mean().to_list()[0][0]*2
            if len(base_exp.Type.filter(id = 21)) == 1:
                data2 = data[(f.type == 1),:]
                data2 = data2[:, mean(f.z), by(f.time)]
                height = data2[:-50:, mean(f.z)].to_list()*2
        counts, bins, bars = plt.hist(points, 200)
        len_points = points.nrows
        data_dic = {'counts':counts, 'bins':bins[:-1]}
        df = pd.DataFrame(data=data_dic)
        anz_part.append(len_points)
        dfs[i] = df

    directory = 'Private/02_Dataframes/LMP_Cosolvent_Analysis/'+'LCA_' +base_exp.Name
    if not os.path.exists(directory):
        os.makedirs(directory)
    dfs[1].to_csv(directory+'/Hist_Mono.csv')
    dfs[2].to_csv(directory+'/Hist_H2O.csv')
    dfs[3].to_csv(directory+'/Hist_EtOH.csv')
    item = LMP.objects.get(id = pk) 
    item.lmpcosolventanalysis_set.all().delete()
    entry = LMPCosolventAnalysis(Name = 'LCA_' +base_exp.Name, Anz_H2O = anz_part[2], Anz_EtOH = anz_part[1], 
                                 Height = height, Link_Hist_Mono = directory+'/Hist_Mono.csv', 
                                 Link_Hist_H2O = directory+'/Hist_H2O.csv', Link_Hist_EtOH = directory+'/Hist_EtOH.csv',
                                 Exp = base_exp)
    entry.save()
    del data

def ana_lmp_cosolvent_err(pk, times_back = 100):
    data = Load_Data.Load_LMP_cosolvent(pk, 'polymer_cosolvent.out')
    times = dt.unique(data['time']).sort('time')

    base_exp = ExpBase.objects.get(id = pk)
    anz_part = []
    dfs = {}
    for i in [1,2,3]:
        if data[((f.type == i )& (f.time > times[-times_back,:])), :].shape[0] == 0:
            df = pd.DataFrame([[0,0,0]], columns=['Position', '#_counts', 'Error'])
            dfs[i] = df
            anz_part.append(0)
            continue
        d_z = data[((f.type == i )& (f.time > times[-times_back,:])), :]

        z_positions = np.asarray(d_z[:,f.z])
        time_steps = np.asarray(d_z[:,f.time])
        i_z_max = int(d_z[:,f.z].max()[0,0])

        bins = np.arange(0, i_z_max+3, 1)
        histograms = np.array([np.histogram(z_positions[time_steps == t], bins=bins)[0] for t in np.unique(time_steps)])

        mean_histogram = histograms.mean(axis=0)
        std_histogram = histograms.std(axis=0)

        positions = np.linspace(0.5,i_z_max+1.5,i_z_max+2)
        counts = mean_histogram
        errors = std_histogram
        # Calculate the center of mass
        center_of_mass = np.sum(positions * counts) / np.sum(counts)

        # Calculate the error in the center of mass
        weighted_positions = positions * counts
        sum_counts = np.sum(counts)
        sum_weighted_positions = np.sum(weighted_positions)

        # Error propagation formula
        error_center_of_mass = np.sqrt(np.sum((positions * errors / sum_counts)**2))

        df = pd.DataFrame([np.linspace(0.5,i_z_max+1.5,i_z_max+1), mean_histogram, std_histogram]).T
        df.columns =['Position', '#_counts', 'Error']


        if i == 1:
            height = center_of_mass*2
            height_err = error_center_of_mass*2

        points = data[((f.type == i )& (f.time == times[-1, :])), f.z]
        len_points = points.nrows
        anz_part.append(len_points)
        dfs[i] = df

    directory = 'Private/02_Dataframes/LMP_Cosolvent_Analysis/'+'LCA_' +base_exp.Name
    if not os.path.exists(directory):
        os.makedirs(directory)
    dfs[1].to_csv(directory+'/Hist_Mono_err.csv')
    dfs[2].to_csv(directory+'/Hist_H2O_err.csv')#should be EtOH
    dfs[3].to_csv(directory+'/Hist_EtOH_err.csv')
    item = LMP.objects.get(id = pk) 
    item.lmpcosolventanalysis_set.all().delete()
    entry = LMPCosolventAnalysis(Name = 'LCA_' +base_exp.Name, Anz_H2O = anz_part[2], Anz_EtOH = anz_part[1], 
                                 Height = height, Height_Err = height_err, Link_Hist_Mono = directory+'/Hist_Mono_err.csv', 
                                 Link_Hist_H2O = directory+'/Hist_H2O_err.csv', Link_Hist_EtOH = directory+'/Hist_EtOH_err.csv',
                                 Exp = base_exp)
    entry.save()
    del data