import glob, os
import pandas as pd
from Exp_Main.models import OCA, ExpBase, ExpPath, RSD, DAF, SFG
from Analysis.models import OszAnalysis
from Analysis.models import DafAnalysis
from Exp_Sub.models import LSP, MFR, CAP
from dbfread import DBF
from Lab_Misc import General
import datetime
from django.apps import apps
import numpy as np
from django.utils import timezone
from functools import reduce

from datatable import (dt, fread, f, by, ifelse, update, sort,
                       count, min, max, mean, sum, rowsum)
import numpy as np

cwd = os.getcwd()
rel_path = General.get_BasePath()

def Load_from_Model(ModelName, pk):
    if ModelName == 'OCA':
        return Load_OCA(pk)
    if ModelName == 'RSD':
        return Load_RSD(pk)
    if ModelName == 'LSP':
        return Load_LSP(pk)
    if ModelName == 'MFL':
        return Load_MFL(pk)
    if ModelName == 'MFR':
        return Load_MFR(pk)
    if ModelName == 'HME':
        return Load_HME(pk)
    if ModelName == 'SEL':
        return Load_SEL(pk)
    if ModelName == 'TCM':
        return Load_TCM(pk)
    if ModelName == 'HIA':
        return Load_HIA(pk)
    if ModelName == 'DAF':
        return Load_sliced_DAF(pk)
    if ModelName == 'CAP':
        return Load_CAP(pk)
    if ModelName == 'SFG':
        return Load_SFG(pk)

def conv(x):
    return x.replace(',', '.').encode()

def Load_SFG(pk):
    entry = SFG.objects.get(id = pk)
    file = os.path.join( rel_path, entry.Link)
    try:
        if file[-9:] == '_data.txt':
            data = np.genfromtxt((conv(x) for x in open(file)), delimiter='	', skip_header=5, names=['Wellenzahl', 'smth_1', 'smth_2', 'Signal'])
        else:
            data = np.genfromtxt(file, delimiter=',', skip_header=0, names=['Wellenzahl', 'Signal'])
    except:
        data = pd.read_csv(file, sep='	', )
        data.columns = ["Wellenzahl", "Signal"]
        data = data[pd.to_numeric(data.Wellenzahl, errors='coerce').notnull()]
    return data

def Load_LMP_cosolvent(pk, file_name):
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
    df = pd.read_excel(file)#, 'Tabelle1')
    new_vals = df[df>1]/1000000#correct for wrong format
    Curr_Dash = entry.Dash
    df.update(new_vals)
    df = df.rename(columns = {'Thickness # 3':'Thickness_Brush'})
    df = df.rename(columns = {'Thickness # 4':'Thickness_Brush'})
    df["Time (min.)"] = Curr_Dash.Start_datetime_elli + pd.TimedeltaIndex(df["Time (min.)"], unit='m')
    df["time"] = df["Time (min.)"].dt.tz_convert(timezone.get_current_timezone())
    df['time_loc'] = df["time"]
    return df

def Load_TCM(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    df = pd.read_excel(file)   
    df["time_loc"] = df["time"].dt.tz_localize(timezone.get_current_timezone()) 
    return df

def Load_HIA(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    df = pd.read_csv(file, sep=';', error_bad_lines=False, decimal = '.')  
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
            Sub_Exp.Gas.first().Name
            data[Sub_Exp.Name + '_' + Sub_Exp.Gas.first().Name] = data_sub
        except:
            data[Sub_Exp.Name] = data_sub
    return data

def get_subs_by_model(pk, sub_model):
    # sub_model = 'mfr'
    main_entry = General.get_in_full_model(pk)
    main_model = str.lower(main_entry.Device.Abbrev)
    model = apps.get_model('Exp_Sub', sub_model)
    data = {}
    mfrs = model.objects.filter(**{main_model: ExpBase.objects.get(id = pk)}).all()
    for mfr in mfrs:
        try:
            mfr.Gas.first().Name
            data[mfr.Name + '_' + mfr.Gas.first().Name] = Load_from_Model(mfr.Device.Abbrev, mfr.id)
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
    for file in glob.glob("*.xlsx"):
        if file[0:4] == 'Drop':
            Drops[file[:-5]] = pd.read_excel(file)
            Drops_names.append(file[:-5])
    os.chdir(cwd)
    dropss = pd.concat(Drops, keys=Drops_names)
    dropss['time_loc'] = dropss['abs_time'].dt.tz_localize(timezone.get_current_timezone())
    return dropss

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
    return MFL_N2_data

def Load_MFR(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link)
    data = pd.read_csv(file, sep=' ', error_bad_lines=False)
    data['date_time'] = pd.to_datetime(data['date'] + '_' + data['time'], format='%Y-%m-%d_%H:%M:%S.%f', errors="coerce")
    data['time_loc'] = data['date_time'].dt.tz_localize(timezone.get_current_timezone())
    return data

def Load_csv(entry):
    file = os.path.join( rel_path, entry.Link)
    df = pd.read_csv(file, sep=';', error_bad_lines=False, decimal = ',', parse_dates=[['Date', 'Time']])#skips bad lines
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
    tmp_dt = pd.read_table(file, sep='	', decimal = ',', skiprows = 10, encoding= 'unicode_escape')
    if len(tmp_dt.columns) == 13:
        names = ['Run_No', 'Age', 'CA_M', 'CA_L', 'CA_R', 'CM', 'BD', 'Vol', 'Mag', 'a', 'b', 'c', 'd']
    else:
        names = ['Run_No', 'Age', 'CA_M', 'CA_L', 'CA_R', 'CM', 'BD', 'Vol', 'Mag', 'BI_left', 'BI_right', 'Height']
    data = pd.read_table(file, sep='	', decimal = ',', names = names, skiprows = 10, encoding= 'unicode_escape')
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

        try: # add additional data from left drop edge if there is extra file
            file = os.path.join(rel_path, entry.Link_Additional_Data_CAL)
            tmp_data = pd.read_excel(file, header=0)
            if 'BI_left' in tmp_data.columns:
                tmp_data = tmp_data[['framenumber', 'CA_L', 'contactpointleft', 'leftcontact_y', 'BI_left']]
                data = data.drop(['CA_L', 'contactpointleft', 'leftcontact_y', 'BI_left'], axis = 1)
            else:
                tmp_data = tmp_data[['framenumber', 'CA_L', 'contactpointleft', 'leftcontact_y']]
                data = data.drop(['CA_L', 'contactpointleft', 'leftcontact_y'], axis = 1)
            data = reduce(lambda left, right: pd.merge(left, right, on=['framenumber'], how='outer'), [data, tmp_data])
        except:
            pass

        try: # add additional data from right drop edge if there is extra file
            file = os.path.join(rel_path, entry.Link_Additional_Data_CAR)
            tmp_data = pd.read_excel(file, header=0)
            if 'BI_right' in tmp_data.columns:
                tmp_data = tmp_data[['framenumber', 'CA_R', 'contactpointright', 'rightcontact_y', 'BI_right']]
                data = data.drop(['CA_R', 'contactpointright', 'rightcontact_y', 'BI_right'], axis = 1)
            else:
                tmp_data = tmp_data[['framenumber', 'CA_R', 'contactpointright', 'rightcontact_y']]
                data = data.drop(['CA_R', 'contactpointright', 'rightcontact_y'], axis = 1)
            data = reduce(lambda left, right: pd.merge(left, right, on=['framenumber'], how='outer'), [data, tmp_data])
        except:
            pass
        
        try: # add additional data from 2nd camera if there is extra file
            file = os.path.join(rel_path, entry.Link_Data_2nd_Camera)
            tmp_data = pd.read_excel(file, header=0)
            if 'width / mm' in tmp_data.columns: # width column already exists in file
                tmp_data = tmp_data[['framenumber', 'width', 'width / mm']]
            elif 'width' in tmp_data.columns:
                tmp_data = tmp_data[['framenumber', 'width']]
            elif 'BI_left' in tmp_data.columns: # no width column in file
                tmp_data['width / mm'] = tmp_data['contactpointright'] - tmp_data['contactpointleft']
                tmp_data['width'] = tmp_data['BI_right'] - tmp_data['BI_left']
                tmp_data = tmp_data[['framenumber', 'width', 'width / mm']]
            else:
                tmp_data['width'] = tmp_data['BI_right'] - tmp_data['BI_left']
                tmp_data = tmp_data[['framenumber', 'width']]
            data = reduce(lambda left, right: pd.merge(left, right, on=['framenumber'], how='outer'), [data, tmp_data])
        except:
            pass

        data['time_loc'] = data['abs_time'].dt.tz_localize(timezone.get_current_timezone())
        data['Age'] = (pd.to_datetime(data['time_loc']) - pd.to_datetime(data['time_loc'].to_numpy()[0])).dt.total_seconds()
        cap_entry = CAP.objects.get(Capillary = entry.Capillary)
        effective_spring_const = cap_entry.Spring_Constant_N_per_m * cap_entry.Effective_Length_mm/(cap_entry.Effective_Length_mm - info["value"]["needle_offset"]*info["value"]["pix_calibration"])
        data['force / mN'] = data['deflection / mm'] * effective_spring_const

    except:
        print("No data file existing for ", entry.Name)
        data = pd.DataFrame()
    
    return data

def Load_CAP(pk):
    entry = General.get_in_full_model_sub(pk)
    file = os.path.join( rel_path, entry.Link_Data)
    data = pd.read_csv(file, skiprows=3, header=None, names=["label", "framenumber", "position"])
    data = data.sort_values(by=["framenumber"]) # times not sorted in file
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
    if isinstance(DashTab.CA_high_degree, float):
        slice_CA_high = (data['CA_L']<DashTab.CA_high_degree) & (data['CA_R']<DashTab.CA_high_degree)
        data = data[slice_CA_high]

    if isinstance(DashTab.CA_low_degree, float):
        slice_CA_low = (data['CA_L']>DashTab.CA_low_degree) & (data['CA_R']>DashTab.CA_low_degree)
        data = data[slice_CA_low]

    if isinstance(DashTab.BD_high_mm, float):
        slice_BD = (data['BI_left']<DashTab.BD_high_mm) & (data['BI_right']<DashTab.BD_high_mm)
        data = data[slice_BD]

    if isinstance(DashTab.BD_low_mm, float):
        slice_BD = (data['BI_left']>DashTab.BD_low_mm) & (data['BI_right']>DashTab.BD_low_mm)
        data = data[slice_BD]

    if isinstance(DashTab.Time_high_sec, float):
        slice_time = data['Age']<DashTab.Time_high_sec
        data = data[slice_time]

    if isinstance(DashTab.Time_low_sec, float):
        slice_time = data['Age']>DashTab.Time_low_sec
        data = data[slice_time]
    try:
        if isinstance(DashTab.Width_high_mm, float):
            slice_width = data['width / mm']<DashTab.Width_high_mm
            data = data[slice_width]

        if isinstance(DashTab.Width_low_mm, float):
            slice_width = data['width / mm']>DashTab.Width_low_mm
            data = data[slice_width]

        if isinstance(DashTab.Force_high_muN, float):
            slice_force = data['force / mN']<1000*DashTab.Force_high_muN
            data = data[slice_force]

        if isinstance(DashTab.Force_low_muN, float):
            slice_force = data['force / mN']>1000*DashTab.Force_low_muN
            data = data[slice_force]
    except:
        pass

    return data


def Load_sub_LSP(Main_id):
    entry = General.get_in_full_model(Main_id)
    Sub_Exp = entry.Sub_Exp.all()
    df = Load_LSP(Sub_Exp[0])
    DashTab = entry.Dash
    time_to_add = 0
    if isinstance(DashTab.Time_diff_pump, float):
        time_to_add = DashTab.Time_diff_pump
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
    #df['date_time'] = temp_time.apply(lambda dt: dt.replace(year=Syringe_pump.Date_time.date().year, month=Syringe_pump.Date_time.date().month, day=Syringe_pump.Date_time.date().day))
    df['time_loc'] = df['date_time'].dt.tz_localize(timezone.get_current_timezone())
    df['Age_dt'] = pd.to_datetime(df["Event time"], format='%H:%M:%S,%f').dt.time
    df['Age_s'] = [time.hour*60*60+time.minute*60+time.second+time.microsecond/1000000 for time in df['Age_dt']]
    return df

def Load_OszAnalysis_in_df(Osz_Ana_id):
    entry = OszAnalysis.objects.get(id = Osz_Ana_id)
    OszBaseParam_inst = entry.OszBaseParam.all()
    Param_columns = ['Max_CL', 'Max_CA', 'Min_CA', 'Min_AdvCA']
    df_ana_res_left = pd.DataFrame(columns=Param_columns)
    df_ana_res_right = pd.DataFrame(columns=Param_columns)
    Drop_parameters = pd.DataFrame(columns=['Drop_Nr'])
    for OszBaseParam_in in OszBaseParam_inst:
        df = pd.DataFrame(columns=Param_columns)
        df.loc[0] = [OszBaseParam_in.Max_CL, OszBaseParam_in.Max_CA, OszBaseParam_in.Min_CA, OszBaseParam_in.Min_AdvCA]
        if OszBaseParam_in.LoR_CL == 'Left':
            df_2 = pd.DataFrame(columns=['Drop_Nr'])
            df_2.loc[0] = OszBaseParam_in.Drop_Nr
            df_ana_res_left = df_ana_res_left.append(df, ignore_index=True)
            Drop_parameters = Drop_parameters.append(df_2, ignore_index=True)
        if OszBaseParam_in.LoR_CL == 'Right':
            df_ana_res_right = df_ana_res_right.append(df, ignore_index=True)
    df_drop_pram = pd.concat([Drop_parameters, df_ana_res_left, df_ana_res_right], keys=['General', 'Left', 'Right'], axis = 1)

    OszFitRes_inst = entry.OszFitRes.all()
    Fit_columns = ['x_pos', 'y_pos', 'Step_width', 'Step_hight']
    df_fit_res_left = pd.DataFrame(columns=Fit_columns)
    df_fit_res_right = pd.DataFrame(columns=Fit_columns)
    df_fit_res_left_error = pd.DataFrame(columns=Fit_columns)
    df_fit_res_right_error = pd.DataFrame(columns=Fit_columns)
    df_drop_nr = pd.DataFrame(columns=[['General'],['General'],['Drop_Nr']])
    drop_nrs = []
    for OszFitRes_in in OszFitRes_inst:
        df = pd.DataFrame(columns=Fit_columns)
        df.loc[0] = [OszFitRes_in.x_pos, OszFitRes_in.y_pos, OszFitRes_in.Step_width, OszFitRes_in.Step_hight]
        if OszFitRes_in.LoR_CL == 'Left':
            if OszFitRes_in.ErroVal == 'Value':
                df_fit_res_left = df_fit_res_left.append(df, ignore_index=True)
                drop_nrs.append(OszFitRes_in.Drop_Nr)
            if OszFitRes_in.ErroVal == 'Error':
                df_fit_res_left_error = df_fit_res_left_error.append(df, ignore_index=True)
        if OszFitRes_in.LoR_CL == 'Right':
            if OszFitRes_in.ErroVal == 'Value':
                df_fit_res_right = df_fit_res_right.append(df, ignore_index=True)
            if OszFitRes_in.ErroVal == 'Error':
                df_fit_res_right_error = df_fit_res_right_error.append(df, ignore_index=True)
    df_fit_res_left = pd.concat([df_fit_res_left, df_fit_res_left_error], keys=['Value', 'Error'], axis = 1)
    df_fit_res_right = pd.concat([df_fit_res_right, df_fit_res_right_error], keys=['Value', 'Error'], axis = 1)
    df_fit_res = pd.concat([df_fit_res_left, df_fit_res_right], keys=['Left', 'Right'], axis = 1)
    df_fit_res = pd.concat([df_drop_nr, df_fit_res], axis = 1)
    df_fit_res.loc[:,('General', 'General', 'Drop_Nr')] = drop_nrs

    OszDerivedRes_inst = entry.OszDerivedRes.all()
    Derived_col = ['Hit_prec', 'Fit_score']
    df_OszDerivedRes_left = pd.DataFrame(columns=Derived_col)
    df_OszDerivedRes_right = pd.DataFrame(columns=Derived_col)
    df_drop_nr = pd.DataFrame(columns=['Drop_Nr'])
    for OszDerivedRes_in in OszDerivedRes_inst:
        df = pd.DataFrame(columns=Derived_col)
        df.loc[0] = [OszDerivedRes_in.Hit_prec, OszDerivedRes_in.Fit_score]
        if OszDerivedRes_in.LoR_CL == 'Left':
            df_2 = pd.DataFrame(columns=['Drop_Nr'])
            df_2.loc[0] = OszDerivedRes_in.Drop_Nr
            df_OszDerivedRes_left = df_OszDerivedRes_left.append(df, ignore_index=True)
            df_drop_nr = df_drop_nr.append(df_2, ignore_index=True)
        if OszDerivedRes_in.LoR_CL == 'Right':
            df_OszDerivedRes_right = df_OszDerivedRes_right.append(df, ignore_index=True)

    df_OszDerivedRes = pd.concat([df_drop_nr, df_OszDerivedRes_left, df_OszDerivedRes_right], keys=['General', 'Left', 'Right'], axis = 1)
    return df_drop_pram, df_fit_res, df_OszDerivedRes

def Load_DAFAnalysis_in_df(DAF_id):
    Exp = DAF.objects.get(id = DAF_id)
    try:
        data_path = os.path.join(General.get_BasePath(), Exp.Link_Result)
        df = pd.read_excel(data_path, header=0, index_col=0)
        columns = df.columns.values
        df = df.to_numpy()
        data = pd.DataFrame([df[-2]], columns=columns)
        errors = pd.DataFrame([df[-1]], columns=columns)
    except:
        print("No analysis results existing for ", Exp.Name)
        data, errors = pd.DataFrame(), pd.DataFrame()
    
    return data, errors
