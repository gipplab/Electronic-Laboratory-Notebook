#from pty import slave_open
from Lab_Misc import Load_Data
import pandas as pd
from Lab_Misc.General import get_LastIndex
from Exp_Main.models import RSD as RSD_model
from datetime import timedelta

class RSD():
    def __init__(self, pk):
        self.pk = pk
        self.entry = RSD_model.objects.get(id = pk)

    def slice_residual(self):
        try:
            self.RSD_data['CA_L'] = self.RSD_data['CA_L'][self.RSD_data['res_left']>0.00001]
            self.RSD_data['CA_R'] = self.RSD_data['CA_R'][self.RSD_data['res_right']>0.00001]
            DashTab = self.entry.Dash
            if isinstance(DashTab.Residual, float):
                self.RSD_data['CA_L'] = self.RSD_data['CA_L'][self.RSD_data['res_left']<DashTab.Residual]
                self.RSD_data['CA_R'] = self.RSD_data['CA_R'][self.RSD_data['res_right']<DashTab.Residual]
                self.RSD_data['CA_M'] = self.RSD_data['CA_M'][(self.RSD_data['res_right']+self.RSD_data['res_left'])<DashTab.Residual]
        except:
            print('No residual found!')

    def Load_all_data(self):
        self.RSD_data = Load_Data.Load_sliced_RSD(self.pk)
        self.RSD_data['CA_M'] = (self.RSD_data['CA_L'] + self.RSD_data['CA_R'])/2
        self.slice_residual()
        self.Sub_RSD_data = Load_Data.get_subs_in_dic(self.pk)

        
        self.RSD_data['Drop_Number'] = 0
        for item in self.RSD_data.index.levels[0]:
            number = item[item.find('_')+1:]
            number = int(number)
            self.RSD_data.loc[item,'Drop_Number'] = number
   
    def correct_times(self):
        if isinstance(self.entry.Dash.Time_diff_pump, float):
            indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'LSP' in s]
            for index in indices:
                self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[index]]]['time_loc'] = self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[index]]]['time_loc'] + timedelta(minutes = self.entry.Dash.Time_diff_pump)
        if isinstance(self.entry.Dash.Time_diff_vid, float):
            self.RSD_data['time_loc'] = self.RSD_data['time_loc'] + timedelta(minutes = self.entry.Dash.Time_diff_vid)

    def calc_speed(self):
        self.RSD_data['speed_left'] = None
        self.RSD_data['speed_right'] = None
        self.RSD_data['speed_left_avg'] = None
        self.RSD_data['speed_right_avg'] = None

        for drop_nr in self.RSD_data['Drop_Number'].unique():

            nr_rol = 5
            self.RSD_data_one = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr][1:].reset_index()
            self.RSD_data_minus_one = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr][:-1].reset_index()

            delta_time = self.RSD_data_one['time_loc']-self.RSD_data_minus_one['time_loc']

            delta_time = delta_time.dt.total_seconds()

            speed_left = (self.RSD_data_one['BI_left']-self.RSD_data_minus_one['BI_left'])/(delta_time)*10**-3*-1
            speed_right = (self.RSD_data_one['BI_right']-self.RSD_data_minus_one['BI_right'])/(delta_time)*10**-3
            
            speed_left = speed_left.to_list()
            speed_left.append(None)
            speed_right = speed_right.to_list()
            speed_right.append(None)

            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_left']= speed_left
            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_right']= speed_right


            avg_right = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr].rolling(nr_rol).mean()['speed_right']
            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_right_avg'] = avg_right
            self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_right_avg'] = self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_right_avg'].shift(-int((nr_rol)/2))
            
            avg_left = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr].rolling(nr_rol).mean()['speed_left']
            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_left_avg'] = avg_left
            self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_left_avg'] = self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_left_avg'].shift(-int((nr_rol)/2))
            

    def Merge_LSP(self):
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'LSP' in s]

        #self.RSD_data = self.RSD_data.dropna()
        '''for index in indices:
            lsp_name = list(self.Sub_RSD_data)[index]
            self.Sub_RSD_data[lsp_name] = self.Sub_RSD_data[lsp_name][self.Sub_RSD_data[lsp_name]['time_loc']>min(self.RSD_data['time_loc'])]'''

        if len(indices)==2:
            lsp_dict = {'time_loc': self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['time_loc'], 
                    'flowrate':self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['Current flow rate']+self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[1]]]['Current flow rate']}
        else:
            print('Wrong amount of LSPs!')

        lsp_dict = pd.DataFrame(lsp_dict)

        self.merged = pd.merge_asof(self.RSD_data.sort_values('time_loc'), lsp_dict, on = 'time_loc')

    def Merge_MFR(self):
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'MFR' in s]
        MFRs = {}
        for index in indices:
            MFR_name = list(self.Sub_RSD_data)[index]
            gas = MFR_name[get_LastIndex(MFR_name,'_')+1:]
            dict_temp = {'time_loc':self.Sub_RSD_data[list(self.Sub_RSD_data)[index]]['time_loc'], 
                        'sccm':self.Sub_RSD_data[list(self.Sub_RSD_data)[index]]['sccm']}
            MFRs[gas] = pd.DataFrame(dict_temp)

        is_first = True
        for item in MFRs:
            if is_first:
                is_first = False
                MFR_merge = MFRs[item]
                first_item = item
                continue
            MFR_merge = pd.merge_asof(MFR_merge.dropna(), MFRs[item].dropna(), on = 'time_loc', suffixes = ['','_'+str(item)])

        MFR_merge = MFR_merge.rename(columns = {'sccm':'sccm_'+str(first_item)})
        MFR_merge_max = MFR_merge.drop(columns='time_loc')
        MFRs_data = {'time_loc':MFR_merge['time_loc'],'gas':MFR_merge_max.idxmax(axis=1).str.replace('sccm_', '')}
        MFRs_data = pd.DataFrame(MFRs_data)

        self.merged = pd.merge_asof(self.merged, MFRs_data, on = 'time_loc')
    
    def Merge_TCM(self):
        self.RSD_data['Drop_Number'] = 0

        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'TCM' in s]

        #self.RSD_data = self.RSD_data.dropna()
        for index in indices:
            lsp_name = list(self.Sub_RSD_data)[index]
            self.Sub_RSD_data[lsp_name] = self.Sub_RSD_data[lsp_name][self.Sub_RSD_data[lsp_name]['time_loc']>min(self.RSD_data['time_loc'])]

        if len(indices)==1:
            lsp_dict = {'time_loc': self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['time_loc'], 
                    'temperature':self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['object temperature']}
        else:
            print('Wrong amount of TCMs!')

        lsp_dict = pd.DataFrame(lsp_dict)

        self.merged = pd.merge_asof(self.merged, lsp_dict, on = 'time_loc')

    def Merge_LSP_MFR(self):
        self.Load_all_data()
        self.correct_times()
        try:
            self.calc_speed()
        except:
            print('No speed calculated')
        self.Merge_LSP()
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'MFR' in s]
        if len(indices)!=0:
            self.Merge_MFR()

    def Merge_LSP_MFR_TCM(self):
        self.Merge_LSP_MFR()
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'TCM' in s]
        if len(indices)!=0:
            self.Merge_TCM()