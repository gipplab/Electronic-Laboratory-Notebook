#from pty import slave_open
from Lab_Misc import Load_Data
import pandas as pd
from Lab_Misc.General import get_LastIndex
from Exp_Main.models import SEL as SEL_model
import numpy as np
import datetime

class SEL():
    def __init__(self, pk):
        self.pk = pk
        self.entry = SEL_model.objects.get(id = pk)

    def Load_all_data(self):
        self.data = Load_Data.Load_from_Model('SEL', self.pk)
        self.subs = Load_Data.get_subs_in_dic(self.pk)

    def mse_slice(self, data_, krit_mse = 5, krit_time = 2):
        #removes data over kirt mse and in interval pm 0,5 krit_time
        data_.loc[data_['MSE']>krit_mse, 'time_diff'] = data_.loc[data_['MSE']>krit_mse, 'time_loc'].diff()
        data_['drop_time'] = False #time around where the MSE gets high
        for k, v in data_.loc[data_['MSE']>krit_mse].groupby((data_['MSE']<=krit_mse).cumsum()):
            data_.loc[v.iloc[:1].index, 'drop_time'] = True
            data_.loc[v.iloc[-1:].index, 'drop_time'] = True
        data_['is_valid'] = True
        data_.loc[data_['MSE']>krit_mse, 'is_valid'] = False

        for i, item in data_[data_['drop_time']==True].T.iteritems():
            data_.loc[(data_['time_loc']>item['time_loc']-datetime.timedelta(minutes = krit_time/2)) & 
                    (data_['time_loc']<item['time_loc']+datetime.timedelta(minutes = krit_time/2)), 'is_valid'] = False
        return data_[data_['is_valid']==True]

    def get_rh(self, T1, T2, RH):
        absMoisture1 = (RH*0.42*np.exp(T1*10*0.006235398)/10)
        RH_at_T = (absMoisture1*10/(0.42*np.exp(T2*10*0.006235398)))
        return RH_at_T
   
  
    def Merge_HIA(self):
        self.Load_all_data()
        if isinstance(self.entry.Dash.Temp_pelt, float):
            temp_plt = self.entry.Dash.Temp_pelt
        else:
            temp_plt = 50

        if isinstance(self.entry.Dash.Krit_mse, float):
            Krit_mse = self.entry.Dash.Krit_mse
        else:
            Krit_mse = 5

        if isinstance(self.entry.Dash.Mse_time_delta, float):
            Mse_time_delta = self.entry.Dash.Mse_time_delta
        else:
            Mse_time_delta = 5


        data = self.mse_slice(self.data, Krit_mse, Mse_time_delta)

        indices = [i for i, s in enumerate(list(self.subs)) if 'HIA' in s]
        if len(indices)<1:
            print('Error')

        self.subs[list(self.subs)[indices[0]]]['RH_at_temp']=self.get_rh(self.subs[list(self.subs)[indices[0]]]['Temperature:'], 
                                                        temp_plt, self.subs[list(self.subs)[indices[0]]]['Humidity:'])

        self.merged = pd.merge_asof(data, self.subs[list(self.subs)[indices[0]]], on = 'time_loc')

