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
   
    def correct_times(self):
        if isinstance(self.entry.Dash.Time_diff_pump, float):
            indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'LSP' in s]
            for index in indices:
                self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[index]]]['time_loc'] = self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[index]]]['time_loc'] + timedelta(minutes = self.entry.Dash.Time_diff_pump)
        if isinstance(self.entry.Dash.Time_diff_vid, float):
            self.RSD_data['time_loc'] = self.RSD_data['time_loc'] + timedelta(minutes = self.entry.Dash.Time_diff_vid)


    def Merge_LSP(self):
        self.RSD_data['Drop_Number'] = 0
        for item in self.RSD_data.index.levels[0]:
            number = item[item.find('_')+1:]
            number = int(number)
            self.RSD_data.loc[item,'Drop_Number'] = number
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'LSP' in s]

        self.RSD_data = self.RSD_data.dropna()
        for index in indices:
            lsp_name = list(self.Sub_RSD_data)[index]
            self.Sub_RSD_data[lsp_name] = self.Sub_RSD_data[lsp_name][self.Sub_RSD_data[lsp_name]['time_loc']>min(self.RSD_data['time_loc'])]

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
            MFR_merge = pd.merge_asof(MFR_merge, MFRs[item], on = 'time_loc', suffixes = ['','_'+str(item)])

        MFR_merge = MFR_merge.rename(columns = {'sccm':'sccm_'+str(first_item)})
        MFR_merge_max = MFR_merge.drop(columns='time_loc')
        MFRs_data = {'time_loc':MFR_merge['time_loc'],'gas':MFR_merge_max.idxmax(axis=1).str.replace('sccm_', '')}
        MFRs_data = pd.DataFrame(MFRs_data)

        self.merged = pd.merge_asof(self.merged, MFRs_data, on = 'time_loc')

    def Merge_LSP_MFR(self):
        self.Load_all_data()
        self.correct_times()
        self.Merge_LSP()
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'MFR' in s]
        if len(indices)!=0:
            self.Merge_MFR()