import pandas as pd
#import matplotlib.pyplot as plt
import numpy as np
import sys
import os
from Lab_Misc.models import OszScriptGen
from Lab_Misc import General

def gen_scripts(pk):
    def gen_gas_script():
        def init_gas():
            with open(path_to_scripts + "Steuerung.txt", 'w') as file:
                file.write('Time to pass 	unit	comport		flowrate\n0	sec	Water	0\n0	sec	Ethanol	0\n0	sec	EtOH-H2O	0\n0	sec	Nitrogen	0\n')
        def flowcontrol_gas(time, cycle, liquid, fin = False):
            Max_flow = {'Water' : str(100), 'Ethanol' : str(100), 'Nitrogen' : str(100)}
            if fin:
                write_flow_to_gas(liquid, time/60, str(0))
                file.write(str(time)+ '	sec	' + liquid + '	' + str(0) + '\n')
            else:
                unit = 'min'
                try:
                    on_cycle[liquid].index(i)
                    file.write(str(time)+ '	' + unit + '	' + liquid + '	' + Max_flow[liquid] + '\n')
                    write_flow_to_gas(liquid, time, Max_flow[liquid])
                except:
                    pass
                try:
                    off_cycle[liquid].index(i)
                    file.write(str(time)+ '	' + unit + '	' + liquid + '	0\n')
                    write_flow_to_gas(liquid, time, 0)
                except:
                    pass
        def write_flow_to_gas(liquid, time, flowrate):
            nonlocal gas_flow
            flowrate = float(flowrate)
            flow_df_item = pd.DataFrame([[cumulated_wait_time,gas_flow[liquid]['flowrate'].iloc[-1]],[0,flowrate]], columns=['time','flowrate'])
            gas_flow[liquid] = gas_flow[liquid].append(flow_df_item)
        def gen_gas_flow():
            gas_flow = {}
            for liquid in Gas_controll['Liquid']:
                gas_flow[liquid] = pd.DataFrame(columns=['time','flowrate'])
                gas_flow[liquid].loc[0] = [0, 0]
            return gas_flow

        gas_flow = gen_gas_flow()

        init_gas()
        fin_liquids = ['Ethanol', 'Water', 'Nitrogen']

        cumulated_wait_time = 30/60
        is_first = True
        with open(path_to_scripts + "Steuerung.txt", 'a') as file:
            for i in range(0,number_of_cycles+1):
                cumulated_wait_time = cycle_times[i]
                for k, liquid in enumerate(Gas_controll['Liquid']):
                    if k == 0:
                        flowcontrol_gas(cumulated_wait_time, i, liquid)
                    else:
                        flowcontrol_gas(0, i, liquid)
                init_flowcontrol_gas = False
        for liquid in Gas_controll['Liquid']:
            with open(path_to_scripts +"Steuerung.txt", 'a') as file:
                cumulated_wait_time =0.1/60
                flowcontrol_gas(0.1, 0, liquid, True)

        for liquid in Gas_controll['Liquid']:
            gas_flow[liquid] = post_precessing_df(gas_flow[liquid])
        return pd.concat(gas_flow, keys=Gas_controll['Liquid'], axis = 1)

    def gen_pump_script():
        def init_liquid(inout):
            with open(path_to_scripts + "Pumpe_" + inout + ".mth", 'w') as file:
                file.write('[MTHFile]\n')
                file.write('Version=1.0\n')
                file.write('DecimalSeparator=.\n')
                file.write('ShortDateFormat=dd.MM.yyyy\n')
                file.write('DateSeparator=.\n')
                file.write('TwoDigitYearCenturyWindow=0\n')
                file.write('[MethodDefinition]\n')
                file.write('MethodName=DISPENS_Mult_1,5_'+ inout +'\n')
                file.write('Description=\n')
                file.write('FlowUnits=ul/min\n')
                file.write('SyringeCount=1\n')
                file.write('CreatedDate=04.09.2019\n')
                file.write('ModifiedDate=05.12.2019\n')
                file.write('LoopEnabled=0\n')
                file.write('StartingStepIndex=-1\n')
                file.write('EndingStepIndex=-1\n')
                file.write('LoopIterations=0\n')
                file.write('[PumpModel]\n')
                file.write('PumpModelId=13\n')
                file.write('ModelName=Legato 100\n')
                file.write('MaxSpeed=159\n')
                file.write('CommandLatency=250\n')
                file.write('[RackModel]\n')
                file.write('RackModelId=74\n')
                file.write('ModelName=LEGATO 110 Infusion/Withdrawal with Single Syringe\n')
                file.write('MaxCapacity=60,00 ml\n')
                file.write('MaxSyringes=1\n')
                file.write('[SyringeModel]\n')
                file.write('SyringeModelId=147\n')
                file.write('ModelName=Glass\n')
                file.write('DiameterInMm=10.3\n')
                file.write('Size=5\n')
                file.write('SizeUnits=ml\n')
                file.write('IsCustom=0\n')
                file.write('[Steps]\n')
                file.write('StepCount='+str(number_of_steps)+'\n')
        def step(step_nr, start_flow, end_flow, duration, inout):
            duration = conv_time(duration, 'min') 
            with open(path_to_scripts +"Pumpe_" + inout + ".mth", 'a') as file:
                file.write('[Step_' + str(step_nr) + ']\n')
                file.write('StartFlow=' + str(start_flow) + '\n')
                file.write('StartFlowUnits=ul/min\n')
                file.write('EndFlow=' + str(end_flow) + '\n')
                file.write('EndFlowUnits=ul/min\n')
                file.write('Duration=' + str(duration) + '\n')
                file.write('IsLinked=0\n')
                file.write('VolumeUnits=ul\n')

        def conv_time(val, unit):
            if unit == 'min':
                return val * 2 * 0.000347222222222222
            if unit == 'sec':
                return val / 30 * 0.000347222222222222

        def scaling_flow(time_flow):
            return (faktor_zeit * time_flow) ** scaling_vol

        def add_scaling_flow(time_flow):
            return (add_with_fakt_zeit * time_flow) ** add_with_scal_vol

        def in_full_drop(time_flow):
            return diff_flow + scaling_flow(time_flow)

        def out_full_drop(time_flow):
            return -add_with_const - add_scaling_flow(time_flow)
        
        def gen_init_osz():
            def fnc_none_break(cycle):
                nonlocal pump_out_df, pump_in_df
                pump_df_item = pd.DataFrame([[0, 0, 'none breake', cycle], [delay, 0, 'none breake', cycle]], 
                                            columns=['time','flowrate', 'state', 'cycle_number'])
                pump_in_df = pump_in_df.append(pump_df_item)
                pump_out_df = pump_out_df.append(pump_df_item)    

            def fnc_pump_in(cycle):
                nonlocal pump_out_df, pump_in_df
                time = init_drop*(factor**(cycle))
                pump_df_item_in = pd.DataFrame([[0, base_flow, 'in', cycle], [time, base_flow, 'in', cycle]], 
                                            columns=['time','flowrate', 'state', 'cycle_number'])
                pump_in_df = pump_in_df.append(pump_df_item_in)
                pump_df_item_out = pd.DataFrame([[0, 0, 'in', cycle], [time, 0, 'in', cycle]], 
                                                columns=['time','flowrate', 'state', 'cycle_number'])
                pump_out_df = pump_out_df.append(pump_df_item_out) 


            def fnc_Full_break(cycle):
                nonlocal pump_out_df, pump_in_df
                time = 5/60
                pump_df_item = pd.DataFrame([[0, 0, 'full breake', cycle], [time, 0, 'full breake', cycle]], 
                                            columns=['time','flowrate', 'state', 'cycle_number'])
                pump_in_df = pump_in_df.append(pump_df_item)
                pump_out_df = pump_out_df.append(pump_df_item) 


            def fnc_pump_out(cycle):
                nonlocal pump_out_df, pump_in_df
                time = init_drop*(factor**(cycle))
                pump_df_item_in = pd.DataFrame([[0, 0, 'out', cycle], [time, 0, 'out', cycle]], 
                                            columns=['time','flowrate', 'state', 'cycle_number'])
                pump_in_df = pump_in_df.append(pump_df_item_in)
                pump_df_item_out = pd.DataFrame([[0, -base_flow, 'out', cycle], [time, -base_flow, 'out', cycle]], 
                                                columns=['time','flowrate', 'state', 'cycle_number'])
                pump_out_df = pump_out_df.append(pump_df_item_out) 

            pump_in_df = pd.DataFrame()
            pump_out_df = pd.DataFrame()
            for cycle in range(number_of_cycles):
                fnc_none_break(cycle)
                fnc_pump_in(cycle)
                fnc_Full_break(cycle)
                fnc_pump_out(cycle)
            fnc_none_break(cycle)
            pump_in_df = pump_in_df.reset_index(drop= True)
            pump_out_df = pump_out_df.reset_index(drop= True)
            pump_in_df['flowrate_out'] = pump_out_df['flowrate']
            pump_in_df = pump_in_df.reindex(columns=['time', 'state' , 'cycle_number', 'flowrate', 'flowrate_out'])
            pump_in_df = pump_in_df.rename(columns={"flowrate": "flowrate_in"})
            return pump_in_df

        def speed_up_osz():
            nonlocal pump_df
            for index in pump_df[(pump_df['time']>max_time)&(pump_df['state']=='in')].index:
                org_time = pump_df.loc[index,'time']
                pump_df.loc[index,'time'] = max_time
                end_flow = base_flow+base_flow*max_time_pls_increase*(org_time-max_time)
                time = (org_time-max_time)*(base_flow+base_flow)/(base_flow+end_flow)
                pump_df_item_in = pd.DataFrame([[0, 'in', pump_df.loc[index,'cycle_number'], base_flow, 0], [time, 'in', pump_df.loc[index,'cycle_number'], end_flow, 0]], 
                                            columns=['time', 'state', 'cycle_number', 'flowrate_in', 'flowrate_out']
                                            , index=[index+0.1,index+0.2])
                pump_df = pump_df.append(pump_df_item_in, ignore_index=False)

            for index in pump_df[(pump_df['time']>max_time)&(pump_df['state']=='out')].index:
                org_time = pump_df.loc[index,'time']
                pump_df.loc[index,'time'] = max_time
                start_flow = -base_flow-base_flow*max_time_pls_increase*(org_time-max_time)
                time = (org_time-max_time)*(base_flow+base_flow)/(base_flow-start_flow)
                pump_df_item_in = pd.DataFrame([[0, 'out', pump_df.loc[index,'cycle_number'], 0, start_flow], [time, 'out', pump_df.loc[index,'cycle_number'], 0, -base_flow]], 
                                            columns=['time', 'state', 'cycle_number', 'flowrate_in', 'flowrate_out']
                                            , index=[index+0.1-2,index+0.2-2])
                pump_df = pump_df.append(pump_df_item_in, ignore_index=False)

            pump_df = pump_df.sort_index().reset_index(drop=True)

        def ethanol_compensation():
            def pump_in(cycle):
                nonlocal pump_df
                indexs = pump_df[(pump_df['cycle_number']==cycle)&(pump_df['state']=='in')].index
                time = pump_df.loc[indexs[1], 'time']
                time_flow = conv_time(time, 'min')
                prev_time = 0
                for i_indexs in list(np.arange(1,len(indexs),2)):
                    if i_indexs == 1:
                        time = pump_df.loc[indexs[1], 'time']
                    else:
                        corr_pseudo_time = (pump_df.loc[indexs[i_indexs], 'flowrate_in']+pump_df.loc[indexs[i_indexs-1], 'flowrate_in'])/(base_flow*2)
                        time = prev_time+pump_df.loc[indexs[i_indexs], 'time']*corr_pseudo_time #time would have been needed with baseflow
                    time_flow = conv_time(time, 'min')
                    org_start_base = pump_df.loc[indexs[i_indexs-1], 'flowrate_in']
                    org_end_base = pump_df.loc[indexs[i_indexs], 'flowrate_in']
                    start_flow = org_start_base + in_full_drop(conv_time(prev_time, 'min'))
                    end_flow = org_end_base + in_full_drop(time_flow)
                    pump_df.loc[indexs[i_indexs-1], 'flowrate_in'] = start_flow
                    pump_df.loc[indexs[i_indexs], 'flowrate_in'] = end_flow

                    pump_df.loc[indexs[i_indexs-1], 'flowrate_out'] = -add_with_const - start_flow + org_start_base-add_scaling_flow(conv_time(prev_time, 'min'))
                    pump_df.loc[indexs[i_indexs], 'flowrate_out'] = out_full_drop(time_flow) - end_flow + org_end_base
                    prev_time = time

            def full_break(cycle):
                nonlocal pump_df
                for index in pump_df[(pump_df['cycle_number']==cycle)&(pump_df['state']=='full breake')].index:
                    time_flow = conv_time(init_drop*(factor**int(cycle)), 'min')
                    pump_df.loc[index, 'flowrate_in']=diff_flow + scaling_flow(time_flow)
                    pump_df.loc[index, 'flowrate_out']=out_full_drop(time_flow)-(diff_flow + scaling_flow(time_flow))

            def pump_out(cycle):
                nonlocal pump_df
                indexs = pump_df[(pump_df['cycle_number']==cycle)&(pump_df['state']=='out')].index
                time = pump_df.loc[indexs[len(indexs)-1], 'time']
                time_flow = conv_time(time, 'min')
                prev_time = 0
                for i_indexs in reversed(list(np.arange(1,len(indexs),2))):
                    if i_indexs == len(indexs)-1:
                        time = pump_df.loc[indexs[len(indexs)-1], 'time']
                    else:
                        corr_pseudo_time = (pump_df.loc[indexs[i_indexs], 'flowrate_out']+pump_df.loc[indexs[i_indexs-1], 'flowrate_out'])/(-base_flow*2)
                        time = prev_time+pump_df.loc[indexs[i_indexs], 'time']*corr_pseudo_time #time would have been needed with baseflow
                    time_flow = conv_time(time, 'min')
                    org_start_base = pump_df.loc[indexs[i_indexs-1], 'flowrate_out']
                    org_end_base = pump_df.loc[indexs[i_indexs], 'flowrate_out']
                    start_flow = diff_flow + scaling_flow(time_flow)
                    end_flow = diff_flow + in_full_drop(conv_time(prev_time, 'min'))
                    pump_df.loc[indexs[i_indexs-1], 'flowrate_in'] = start_flow
                    pump_df.loc[indexs[i_indexs], 'flowrate_in'] = end_flow

                    pump_df.loc[indexs[i_indexs-1], 'flowrate_out'] = out_full_drop(time_flow) - start_flow + org_start_base
                    pump_df.loc[indexs[i_indexs], 'flowrate_out'] = -add_with_const - end_flow + org_end_base - add_scaling_flow(conv_time(prev_time, 'min'))
                    prev_time = time

            if 'Ethanol' in on_cycle:
                for cycle in on_cycle['Ethanol']:
                    pump_in(cycle)
                    full_break(cycle)
                    pump_out(cycle)

        def gen_pump_files(flowrate):
            inout = flowrate[flowrate.find('_')+1:]
            init_liquid(inout)
            j= 0
            total_vol = 0
            total_duration = 0
            for index in list(np.arange(1,len(pump_df),2)):
                duration = pump_df.loc[index]['time']
                start_flow = pump_df.loc[index-1][flowrate]
                end_flow = pump_df.loc[index][flowrate]
                step(j, start_flow, end_flow, duration, inout)
                total_vol += (start_flow+end_flow)/2*duration
                total_duration += duration
                j+=1
            print('Total volume in ml:')
            print(total_vol/1000)
            print('Total duration in h:')
            print(total_duration/60)

        pump_df = gen_init_osz()

        speed_up_osz()

        ethanol_compensation()

        pump_df = post_precessing_df(pump_df)

        number_of_steps = int(len(pump_df)/2)

        gen_pump_files('flowrate_in')
        gen_pump_files('flowrate_out')
        cycle_times = [0.01]
        for cycle in range(number_of_cycles):
            cycle_times.append(pump_df.loc[(pump_df['state']=='out')&(pump_df['cycle_number']==cycle)].iloc[-1]['abs_time'])
        return pump_df, cycle_times

    def gen_cam_script():
        with open(path_to_scripts + "Kamera.tcl", 'w') as file:
            file.write('dcc do LiveViewWnd_Show\n')
            for cycle_time in cycle_times[1:]:
                file.write('after '+str(int(delay*60*1000))+'\n')
                if cycle_time-delay > 25:
                    cycle_rest_time = cycle_time-delay
                    while cycle_rest_time > 25+10/60:
                        file.write('dcc do LiveViewWnd_StartRecord\n')
                        file.write('after '+str(int((25)*60*1000))+'\n')
                        file.write('dcc do LiveViewWnd_StopRecord\n')
                        file.write('after '+str(10000)+'\n')
                        cycle_rest_time = cycle_rest_time-25-10/60
                    file.write('dcc do LiveViewWnd_StartRecord\n')
                    file.write('after '+str(int((cycle_rest_time)*60*1000))+'\n')
                    file.write('dcc do LiveViewWnd_StopRecord\n')
                else:
                    file.write('dcc do LiveViewWnd_StartRecord\n')
                    file.write('after '+str(int((cycle_time-delay)*60*1000))+'\n')
                    file.write('dcc do LiveViewWnd_StopRecord\n')
            file.write('after 5000\n')
            file.write('dcc do LiveViewWnd_Hide\n')

    def gen_on_off_cycle():
        on_cycle = {}
        off_cycle = {}
        for i in range(len(Gas_controll)):
            on_cycle_i = []
            for start_number in Gas_controll.iloc[i]['Start_number']:
                on_cycle_i = on_cycle_i + list(range(start_number, number_of_cycles, Gas_controll.iloc[i]['Periodicity']))
            off_cycle_i = []
            for off_number in range(Gas_controll.iloc[i]['Periodicity']):
                try:
                    Gas_controll.iloc[i]['Start_number'].index(off_number)
                except:
                    off_cycle_i = off_cycle_i + list(range(off_number, number_of_cycles+1, Gas_controll.iloc[i]['Periodicity']))
            on_cycle[Gas_controll.iloc[i]['Liquid']] = on_cycle_i
            off_cycle[Gas_controll.iloc[i]['Liquid']] = off_cycle_i
        return on_cycle, off_cycle

    def get_abs_times(times):
        abs_time = [0]
        for item in times:
            abs_time.append(abs_time[-1]+item)
        return abs_time[1:]

    def post_precessing_df(df):
        df = df.reset_index()
        df['abs_time'] = get_abs_times(df['time'])
        return df

    def string_to_list_int(string):
        ints = []
        sep = ','
        if sep in string:
            rem_string = string
            for i in range(string.count(sep)):
                ind = rem_string.index(sep)
                ints.append(int(rem_string[0:ind]))
                rem_string = rem_string[ind+1:]
            ints.append(int(rem_string))
        else:
            ints.append(int(string))
        return ints

    def gen_temperatures():
        temp_a = Temperatures.split(';')
        Temp_correct = False
        try:
            for temp in temp_a:    
                float(temp)
            if len(temp_a) != len(cycle_times)-1:
                raise Exception('Wrong number of Temperatures')
            Temp_correct = True
        except:
            print('Temperature invailid')
            return []
        if Temp_correct:
            data = {'temperature [°C]':temp_a, 'duration [min]':cycle_times[1:]}
            df = pd.DataFrame(data)
            df.to_csv(path_to_scripts+'temperatures.txt', index=None, sep=' ', mode='w')
            return df

    entry = OszScriptGen.objects.get(id = pk)

    path_to_scripts = os.path.join('Private/01_Scripts/Osz_gas_scripts', entry.Name)+'/'
    path_to_df = os.path.join('Private/02_Dataframes/Osz_Gas', entry.Name)+'/'
    if not os.path.exists(path_to_scripts):
        os.makedirs(path_to_scripts)
    if not os.path.exists(path_to_df):
        os.makedirs(path_to_df)
    cwd = os.getcwd()

    init_drop = entry.init_drop
    factor = entry.factor
    delay = entry.delay
    number_of_cycles = entry.number_of_cycles
    max_time = entry.max_time
    max_time_pls_increase = entry.max_time_pls_increase

    liquids = []
    Periodicity = []
    Start_number = []
    for gas in entry.Gas.all():
        liquids.append(gas.Name_of_gas.Name)
        Periodicity.append(gas.Periodicity)
        Start_number.append(string_to_list_int(gas.StartNumber)) 

    Gas_controll = pd.DataFrame(liquids, columns=['Liquid'])
    Gas_controll['Periodicity'] = Periodicity
    Gas_controll['Start_number'] = Start_number

    on_cycle, off_cycle = gen_on_off_cycle()

    base_flow = entry.base_flow
    diff_flow = entry.diff_flow
    faktor_zeit = entry.faktor_zeit
    scaling_vol = entry.scaling_vol
    add_with_const = entry.add_with_const
    add_with_fakt_zeit = entry.add_with_fakt_zeit
    add_with_scal_vol = entry.add_with_scal_vol
    Temperatures = entry.Temperatures


    pump_df, cycle_times = gen_pump_script()
    cycle_times_ = cycle_times
    cycle_times__ = [0.01]
    for i in range(len(cycle_times_)-1):
        cycle_times__.append(cycle_times_[i+1]-cycle_times_[i])
    cycle_times = cycle_times__

    gas_flow = gen_gas_script()

    gen_cam_script()
    temps = gen_temperatures()

    path_to_df
    pump_df.to_pickle(path_to_df + "pump_df.pkl")
    gas_flow.to_pickle(path_to_df + "gas_flow_df.pkl")
    entry.Link_folder_script = os.path.join(cwd[cwd.find(General.BaseFolderName):], path_to_scripts)
    entry.Link_pump_df = os.path.join(cwd[cwd.find(General.BaseFolderName):], path_to_df, "pump_df.pkl")
    entry.Link_gas_df = os.path.join(cwd[cwd.find(General.BaseFolderName):], path_to_df, "gas_flow_df.pkl")
    if len(temps)>0:
        temps.to_pickle(path_to_df + "temps_df.pkl")
        entry.Link_temperatures_df = os.path.join(cwd[cwd.find(General.BaseFolderName):], path_to_df, "temps_df.pkl")
    entry.save()