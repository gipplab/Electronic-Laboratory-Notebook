import glob, os
import pandas as pd
from Exp_Main.models import OCA, ExpBase, ExpPath, RSD
from Analysis.models import OszAnalysis
from Exp_Sub.models import LSP, MFR
from Lab_Misc import General
import datetime
import numpy as np
from django.utils import timezone

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

def Load_RSD_subs(pk):
    Gases = {}
    mfrs = MFR.objects.filter(rsd = RSD.objects.get(id = pk)).all()
    for mfr in mfrs:
        Gases[mfr.Gas.first().Name] = Load_MFR(mfr.id)

    Pump = {}
    lsps = LSP.objects.filter(rsd = RSD.objects.get(id = pk)).all()
    for lsp in lsps:
        Pump[lsp.Name] = Load_LSP(lsp.id)

    return pd.concat(Gases), pd.concat(Pump)

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
    Humidity_data = Load_dfb(pk)
    Humidity_data['UHRZEIT'] = pd.to_datetime(Humidity_data['DATUM'] + Humidity_data['UHRZEIT'], format='%d.%m.%Y    %H:%M:%S', errors="coerce")
    Humidity_data['time'] = Humidity_data['UHRZEIT'].dt.tz_localize(timezone.get_current_timezone())
    return Humidity_data

def Load_dfb(entry):
    file = os.path.join( rel_path, entry.Link)
    table = DBF(file, load=True)
    df = pd.DataFrame(iter(table))
    return df

def Load_OCA(Main_id):
    entry = OCA.objects.get(id = Main_id)
    file = os.path.join( rel_path, entry.Link_Data)
    data = pd.read_table(file, sep='	', decimal = ',', names = ['Run_No', 'Age', 'CA_M', 'CA_L', 'CA_R', 'CM', 'BD', 'Vol', 'Mag', 'BI_left', 'BI_right', 'Height'], skiprows = 10)
    data['Age'] = data['Age']/1000
    slice_CA_high = (data['CA_L']<1800) & (data['CA_R']<1800)
    data = data[slice_CA_high]
    os.chdir(cwd)
    return data

def Load_sliced_OCA(Main_id):
    data = Load_OCA(Main_id)
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