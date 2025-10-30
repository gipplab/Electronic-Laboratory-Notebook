#from pty import slave_open
from Lab_Misc import Load_Data
import pandas as pd
from Lab_Misc.General import get_LastIndex
from Exp_Main.models import RSD as RSD_model
from datetime import timedelta
import numpy as np

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


            avg_right = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr]['speed_right'].rolling(nr_rol).mean()
            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_right_avg'] = avg_right
            self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_right_avg'] = self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_right_avg'].shift(-int((nr_rol)/2))
            
            avg_left = self.RSD_data[self.RSD_data['Drop_Number']==drop_nr]['speed_left'].rolling(nr_rol).mean()
            self.RSD_data.loc[self.RSD_data['Drop_Number']==drop_nr,'speed_left_avg'] = avg_left
            self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_left_avg'] = self.RSD_data.loc[self.RSD_data['Drop_Number'] == drop_nr, 'speed_left_avg'].shift(-int((nr_rol)/2))
            

    def Merge_LSP(self, interval=2):
        indices = [i for i, s in enumerate(list(self.Sub_RSD_data)) if 'LSP' in s]

        if len(indices) == 2:
            lsp_dict = {
                'time_loc': self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['time_loc'],
                'flowrate': self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[0]]]['Current flow rate'] +
                            self.Sub_RSD_data[list(self.Sub_RSD_data)[indices[1]]]['Current flow rate']
            }
        else:
            print('Wrong amount of LSPs!')
            return

        lsp_dict = pd.DataFrame(lsp_dict)

        # Calculate the ratio
        lsp_dict['time_diff'] = lsp_dict['time_loc'].diff().dt.total_seconds().fillna(0)
        lsp_dict['flow_diff'] = lsp_dict['flowrate'].diff().fillna(0)
        lsp_dict['ratio'] = lsp_dict['flow_diff'] / lsp_dict['time_diff']

        # Add time steps every n seconds if the time diff is larger than n seconds
        new_rows = []
        for i in range(len(lsp_dict) - 1):
            new_rows.append(lsp_dict.iloc[i])
            time_diff = (lsp_dict.iloc[i + 1]['time_loc'] - lsp_dict.iloc[i]['time_loc']).total_seconds()
            if time_diff > interval:
                num_steps = int(time_diff // interval)
                for step in range(1, num_steps + 1):
                    new_time = lsp_dict.iloc[i]['time_loc'] + pd.Timedelta(seconds=step * interval)
                    new_row = lsp_dict.iloc[i].copy()
                    new_row['time_loc'] = new_time
                    if pd.notna(lsp_dict.iloc[i + 1]['ratio']):
                        new_row['flowrate'] += step * lsp_dict.iloc[i + 1]['ratio'] * interval
                    new_row['time_diff'] = np.nan
                    new_row['flow_diff'] = np.nan
                    new_row['ratio'] = np.nan
                    new_rows.append(new_row)
        new_rows.append(lsp_dict.iloc[-1])
        lsp_with_steps = pd.DataFrame(new_rows).reset_index(drop=True)

        # Check for null values in the 'time_loc' column
        if self.RSD_data['time_loc'].isnull().any():
            print("Null values found in 'time_loc' column of RSD_data")
            # Handle null values, e.g., by filling them or dropping rows with null values
            self.RSD_data = self.RSD_data.dropna(subset=['time_loc'])

        self.merged = pd.merge_asof(self.RSD_data.sort_values('time_loc'), lsp_with_steps, on='time_loc')

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
        MFRs_data = {
            'time_loc': MFR_merge['time_loc'],
            'gas': MFR_merge_max.idxmax(axis=1).astype(str).str.replace('sccm_', '')
        }
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


    def _determine_contact_angle_types(self):
        self.RSD_data['CA_L_type'] = np.where(self.RSD_data['speed_left'] > 0.000002, 'advancing', 
                                              np.where(self.RSD_data['speed_left'] < -0.000002, 'receding', 'stationary'))
        self.RSD_data['CA_R_type'] = np.where(self.RSD_data['speed_right'] > 0.000002, 'advancing', 
                                              np.where(self.RSD_data['speed_right'] < -0.000002, 'receding', 'stationary'))

    """ def correlate_contact_angles(self, position_col, ca_col, ca_type_col, threshold=0.1):
        df = self.RSD_data
        df_shifted = df.copy()
        df_shifted['Drop_Number'] = df_shifted['Drop_Number'].shift(-1)
        
        merged_df = df.merge(df_shifted, on='Drop_Number', suffixes=('', '_next'))
        
        mask = (
            (merged_df[position_col] >= merged_df[position_col + '_next'] - threshold) &
            (merged_df[position_col] <= merged_df[position_col + '_next'] + threshold) &
            (merged_df[ca_type_col] == 'receding') &
            (merged_df[ca_type_col + '_next'] == 'advancing')
        )
        
        correlations = merged_df[mask][['Drop_Number', position_col, ca_col, ca_col + '_next']]
        correlations.columns = ['Drop_Number', 'Position', 'Receding_CA', 'Advancing_CA']
        
        return correlations """
    def correlate_contact_angles(self, position_col, ca_col, ca_type_col, threshold=0.1):
        correlations = []
        drop_numbers = self.RSD_data['Drop_Number'].unique()
        
        for i in range(len(drop_numbers) - 1):
            drop_num1 = drop_numbers[i]
            drop_num2 = drop_numbers[i + 1]
            
            drop1 = self.RSD_data[self.RSD_data['Drop_Number'] == drop_num1]
            drop2 = self.RSD_data[self.RSD_data['Drop_Number'] == drop_num2]
            
            for pos in drop1[position_col].unique():
                receding_ca = drop1[
                    (drop1[position_col] >= pos - threshold) & 
                    (drop1[position_col] <= pos + threshold) & 
                    (drop1[ca_type_col] == 'receding')
                ][ca_col].mean()
                
                advancing_ca = drop2[
                    (drop2[position_col] >= pos - threshold) & 
                    (drop2[position_col] <= pos + threshold) & 
                    (drop2[ca_type_col] == 'advancing')
                ][ca_col].mean()
                
                if not pd.isna(receding_ca) and not pd.isna(advancing_ca):
                    correlations.append((drop_num1, pos, receding_ca, advancing_ca))
        
        return correlations

    def get_correlations(self):
        self._determine_contact_angle_types()
        correlations_left = self.correlate_contact_angles('BI_left', 'CA_L', 'CA_L_type')
        correlations_right = self.correlate_contact_angles('BI_right', 'CA_R', 'CA_R_type')
        
        correlations_left_df = pd.DataFrame(correlations_left, columns=['Drop_Number', 'Position', 'Receding_CA', 'Advancing_CA'])
        correlations_right_df = pd.DataFrame(correlations_right, columns=['Drop_Number', 'Position', 'Receding_CA', 'Advancing_CA'])
        
        return correlations_left_df, correlations_right_df