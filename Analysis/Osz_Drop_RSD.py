import glob, os
import pandas as pd
import numpy as np
import datetime
from Lab_Misc import General, Load_Data
from Exp_Main.models import OCA, ExpPath
from Analysis.models import OszAnalysis, OszBaseParam, OszFitRes, OszDerivedRes
from Exp_Sub.models import LSP
from Analysis.RSD import RSD

from pathlib import Path
from scipy.optimize import curve_fit
from scipy.signal import lfilter

def stufen_fit(x,a,b,c,d):
    #c = stufen höhe
    #a = stufen breite größer steiler
    #b = stufen position x
    #d = stufen pos y
    return c/(1+np.exp(-a*(x-b)))+d

def Osz_Drop_Analysis(Main_id):
    
    def smoothen_curve(in_array):
        if len(in_array)>0:
            n = 3+int(len(in_array)/200)  # the larger n is, the smoother curve will be
            b = [1.0 / n] * n
            a = 1
            in_array_zero = in_array.iloc[0]
            in_array = in_array-in_array_zero
            out_array = lfilter(b,a,in_array)+in_array_zero
        else:
            out_array = [0]
        return out_array

    def get_largest_1_per(in_array, Name_col):
        if len(in_array)>100:
            largest_1_per = in_array.nlargest(int(len(in_array)/100), Name_col)
            largest_1_per_av = largest_1_per.mean()[Name_col]
        else:
            largest_1_per = in_array.nlargest((1), Name_col)
            largest_1_per_av = largest_1_per.mean()[Name_col]
        return largest_1_per_av

    def get_smallest_1_per(in_array, Name_col):
        if len(in_array)>100:
            smallest_1_per = in_array.nsmallest(int(len(in_array)/100), Name_col)
            smallest_1_per_av = smallest_1_per.mean()[Name_col]
        else:
            smallest_1_per = in_array.nsmallest((1), Name_col)
            smallest_1_per_av = smallest_1_per.mean()[Name_col]
        return smallest_1_per_av

    def get_max_of_drops(Name_col):
        Max_size = []
        for Drop_Nr in Drop_parameters['Drop Numbers']:
            smooth_data = smoothen_curve(data.loc[data['Drop_Number']==Drop_Nr, Name_col])
            smooth_data = pd.DataFrame(data=smooth_data, columns=['smooth_data'])
            Max_size.append(get_largest_1_per(smooth_data, 'smooth_data'))
        return Max_size

    def get_min_of_drops(Name_col):
        Min_size = []
        for Drop_Nr in Drop_parameters['Drop Numbers']:
            smooth_data = smoothen_curve(data.loc[data['Drop_Number']==Drop_Nr, Name_col])
            smooth_data = pd.DataFrame(data=smooth_data, columns=['smooth_data'])
            Min_size.append(get_smallest_1_per(smooth_data, 'smooth_data'))
        return Min_size

    def get_min_Adv_of_drops(Name_col):
        Min_size = []
        for Drop_Nr in Drop_parameters['Drop Numbers']:
            smooth_data = smoothen_curve(data.loc[(data['Drop_Number']==Drop_Nr)&(data['flowrate']>0), Name_col])
            smooth_data = pd.DataFrame(data=smooth_data, columns=['smooth_data'])
            Min_size.append(get_smallest_1_per(smooth_data, 'smooth_data'))
        return Min_size

    def fit_step(L_or_R):
        Values = []
        Errors = []
        if L_or_R == 'L':
            BI = 'BI_left Abs'
            CA = 'CA_L'
            RL = 'Left'
        if L_or_R == 'R':
            BI = 'BI_right'
            CA = 'CA_R'
            RL = 'Right'
        for Drop_Nr in Drop_parameters['General']['Drop Numbers']:
            if Drop_Nr==1:
                pass
            else:
                try:
                    if Drop_Nr>2:
                        min_dia = abs(Drop_parameters.loc[Drop_parameters['General']['Drop Numbers'] == Drop_Nr-2, (RL, 'Max CL')].iloc[0])
                    else:
                        min_dia = 0
                    Area_slice = (data['Drop_Nr']==Drop_Nr)&(data['Flowrate']>0)&(data[BI]>min_dia)
                    ai = [5, 0, 1000]
                    bi = [abs(Drop_parameters.loc[Drop_parameters['General']['Drop Numbers'] == Drop_Nr-1, (RL, 'Max CL')]), 0, 15]
                    min_AdvCA = abs(Drop_parameters.loc[Drop_parameters['General']['Drop Numbers'] == Drop_Nr-1, (RL, 'Min AdvCA')])
                    max_CA = abs(Drop_parameters.loc[Drop_parameters['General']['Drop Numbers'] == Drop_Nr-1, (RL, 'Max CA')])
                    ci = [max_CA-min_AdvCA, 0, 100]
                    di = [min_AdvCA, 0, 150]
                    params = curve_fit(stufen_fit, data.loc[Area_slice, BI], data.loc[Area_slice, CA], p0=[ai[0], bi[0], ci[0], di[0]], 
                                    bounds=([ai[1], bi[1], ci[1], di[1]], [ai[2], bi[2], ci[2], di[2]]))
                    a, b, c, d = params[0]
                    error_val = [] 
                    for i in range(len(params[1])):
                        try:
                            error_val.append(np.absolute(params[1][i][i])**0.5)
                        except:
                            error_val.append( float("NaN") )
                    Values.append(params[0])
                    Errors.append(error_val)
                except:
                    Values.append([float("NaN"), float("NaN"), float("NaN"), float("NaN")])
                    Errors.append([float("NaN"), float("NaN"), float("NaN"), float("NaN")])
        Fit_error = pd.DataFrame(data=Errors, columns=['Step width', 'x pos', 'Step hight', 'y pos'])
        Fit_Value = pd.DataFrame(data=Values, columns=['Step width', 'x pos', 'Step hight', 'y pos'])
        OszFitRess = pd.concat([Fit_Value, Fit_error], keys=['Value', 'Error'], axis = 1)
        return OszFitRess

    entry = General.get_in_full_model(Main_id)
    model_name = entry._meta.model_name
    if model_name == 'oca':
        sub_data = Load_Data.Load_sub_LSP(Main_id)
        data = Load_Data.Load_sliced_OCA(Main_id)
        entry = OCA.objects.get(id = Main_id)
        time_pump = sub_data['Age_s']
        flow_rate = sub_data["Current flow rate"]
    elif model_name == 'rsd':
        data_entry = RSD(Main_id)
        data_entry.Merge_LSP_MFR()
        data = data_entry.merged

    ExistingAnalysis = entry.oszanalysis_set.all()
    if ExistingAnalysis.count() == 0:
        No_existing_Results = True
    else:
        ExistingAnalysis = entry.oszanalysis_set.first()
        ExistingAnalysis_id = ExistingAnalysis.id
        No_existing_Results = False
    '''
    time_pump = np.asarray(time_pump)
    slice_pump = (flow_rate<-1)
    slice_adv_pump = (flow_rate>1)
    times_bigger_1 = time_pump[slice_pump]
    time_points = times_bigger_1[1::2]#[start_index:end_index:step]
    time_points = np.insert(time_points, 0, 0, axis=0)

    zero_slice = (sub_data["Current flow rate"]<-1)
    droptimes = time_pump[zero_slice]
    droptimes = droptimes[1::2]
    droptimes = np.insert(droptimes, 0, 0, axis=0)

    c = []
    i=0

    data['Drop_Nr'] = np.zeros(len(data))
    Drop_Nrs = []
    for i in range(len(droptimes)-1):
        i += 1
        slice_drops = (data['Age'] > droptimes[i-1]) & (data['Age'] < droptimes[i])
        data.loc[slice_drops, 'Drop_Nr'] = i
        Drop_Nrs.append(i)
    i=0
    data['Flowrate'] = np.zeros(len(data))
    ii = np.arange(0, len(sub_data)-1, 1)
    for i in ii:
        slice_pumprates = (data['Age'] >= sub_data.iloc[i]['Age_s']) & (data['Age'] < sub_data.iloc[i+1]['Age_s'])
        data.loc[slice_pumprates, 'Flowrate'] = sub_data.iloc[i]['Current flow rate']
    i=0

    Right_smallest_1_per_av = get_smallest_1_per(data, 'BI_right')
    Left_largest_1_per_av = get_largest_1_per(data, 'BI_left')
    '''
    Drop_parameters = pd.DataFrame(data=list(data['Drop_Number'].unique()), columns=['Drop Numbers'])
    Drop_parameters['Drop center'] = (data['BI_left'].iloc[:10].mean()+data['BI_right'].iloc[:10].mean())/2
    data['BI_right'] = data['BI_right'] - Drop_parameters['Drop center'][0]
    data['BI_left'] = data['BI_left'] - Drop_parameters['Drop center'][0]
    data['BI_left Abs'] = abs(data['BI_left'])

    Drop_parameters_Left = pd.DataFrame(data=get_min_of_drops('BI_left'), columns=['Max CL'])
    Drop_parameters_Right = pd.DataFrame(data=get_max_of_drops('BI_right'), columns=['Max CL'])

    Drop_parameters_Left['Max CA'] = get_max_of_drops('CA_L')
    Drop_parameters_Left['Min CA'] = get_min_of_drops('CA_L')
    Drop_parameters_Right['Max CA'] = get_max_of_drops('CA_R')
    Drop_parameters_Right['Min CA'] = get_min_of_drops('CA_R')
    Drop_parameters_Left['Min AdvCA'] = get_min_Adv_of_drops('CA_L')
    Drop_parameters_Right['Min AdvCA'] = get_min_Adv_of_drops('CA_R')

    Drop_parameters = pd.concat([Drop_parameters, Drop_parameters_Left, Drop_parameters_Right], keys=['General', 'Left', 'Right'], axis = 1)

    if not No_existing_Results:
        ExistingAnalysis.OszBaseParam.all().delete()
        ExistingAnalysis.OszFitRes.all().delete()
        ExistingAnalysis.OszDerivedRes.all().delete()
        ExistingAnalysis.Drop_center = Drop_parameters['General']['Drop center'].iloc[0]
        ExistingAnalysis.save()
        Osz_result = ExistingAnalysis
    else:
        Osz_result = OszAnalysis(Name = 'ARO_' + entry.Name, Drop_center = Drop_parameters['General']['Drop center'].iloc[0], Exp = entry)
    Osz_result.save()
    Left_or_Right = ['Left', 'Right']
    for i_LoR in Left_or_Right:
        for i in range(len(Drop_parameters)):
            Analysis_res = OszBaseParam(Drop_Nr = Drop_parameters['General']['Drop Numbers'].iloc[i], LoR_CL = i_LoR,
                                            Max_CL = Drop_parameters[i_LoR]['Max CL'].iloc[i],
                                            Max_CA = Drop_parameters[i_LoR]['Max CA'].iloc[i],
                                            Min_CA = Drop_parameters[i_LoR]['Min CA'].iloc[i],
                                            Min_AdvCA = Drop_parameters[i_LoR]['Min AdvCA'].iloc[i],)
            Analysis_res.save()
            Osz_result.OszBaseParam.add(Analysis_res)



    Fit_Left = fit_step('L')
    Fit_Right = fit_step('R')
    OszFitRess = pd.concat([Fit_Left, Fit_Right], keys=['Left', 'Right'], axis = 1)

    for i_LoR in Left_or_Right:
        for i_EoV in ['Error', 'Value']:
            for i in range(len(OszFitRess)):
                Fit_res = OszFitRes(Drop_Nr = Drop_parameters['General']['Drop Numbers'].iloc[i+1], LoR_CL = i_LoR, ErroVal = i_EoV,
                                                x_pos = OszFitRess[i_LoR][i_EoV]['x pos'].iloc[i],
                                                y_pos = OszFitRess[i_LoR][i_EoV]['y pos'].iloc[i],
                                                Step_width = OszFitRess[i_LoR][i_EoV]['Step width'].iloc[i],
                                                Step_hight = OszFitRess[i_LoR][i_EoV]['Step hight'].iloc[i],)
                Fit_res.save()
                Osz_result.OszFitRes.add(Fit_res)

    Derived_col = ['Drop_Nr', 'LoR_CL', 'Hit_prec', 'Fit_score']
    Derived = pd.DataFrame(columns=Derived_col)
    for position in Left_or_Right:
        for i in range(len(OszFitRess)):
            fit_rating = 1
            if OszFitRess[position]['Value']['x pos'].loc[i].item()>abs(Drop_parameters[position]['Max CL'].iloc[i+1])+0.5:
                fit_rating = 0
            if OszFitRess[position]['Value']['y pos'].loc[i].item()<Drop_parameters[position]['Min AdvCA'].iloc[i+1]-5:
                fit_rating = 0
            if OszFitRess[position]['Value']['y pos'].loc[i].item()+OszFitRess[position]['Value']['Step hight'].loc[i].item()>Drop_parameters[position]['Max CA'].iloc[i+1]+5:
                fit_rating = 0
            Derived_i = pd.DataFrame(columns=Derived_col)
            Drop_Nr_pram = Drop_parameters['General']['Drop Numbers'].astype(int)
            Drop_Nr_fit = Drop_parameters['General']['Drop Numbers'].iloc[i+1]-1
            diff = abs(Drop_parameters.loc[Drop_Nr_pram == Drop_Nr_fit, (position, 'Max CL')].item())-OszFitRess[position]['Value']['x pos'].loc[i].item()
            diff = abs(1/diff)
            if diff > 20:
                diff = 20
            Derived_i.loc[0] = [Drop_parameters['General']['Drop Numbers'].iloc[i+1], position, diff, fit_rating]
            Derived =  Derived.append(Derived_i, ignore_index=True)

    for i in range(len(Derived)):
        OszDerived = OszDerivedRes(Drop_Nr = Derived['Drop_Nr'].loc[i], LoR_CL = Derived['LoR_CL'].loc[i], Hit_prec = Derived['Hit_prec'].loc[i], Fit_score = Derived['Fit_score'].loc[i])
        OszDerived.save()
        Osz_result.OszDerivedRes.add(OszDerived)
    Osz_result.Hit_prec = Derived['Hit_prec'].mean()
    Osz_result.save()



    Exp_Model = ExpPath.objects.get(Name = str(entry.Device))
    rel_path = General.get_BasePath()
    file_path = os.path.join(rel_path, Exp_Model.PathProcessedData, entry.Date_time.strftime("%Y%m%d"), entry.Sample_name.Name)
    Path(file_path).mkdir(parents=True, exist_ok=True)
    df_Name = str(entry.id) + '_data_Osz_joined_flowrate.pkl'
    data.to_pickle( os.path.join(file_path, df_Name))
    entry.Link_Osz_join_LSP = os.path.join(Exp_Model.PathProcessedData, entry.Date_time.strftime("%Y%m%d"), entry.Sample_name.Name, df_Name)
    entry.save()