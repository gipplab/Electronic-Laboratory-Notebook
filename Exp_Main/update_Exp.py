from .models import ExpPath, ExpBase
from Lab_Misc.General import *
from .models import OCA, CON, SEM, RLD, NEL, DIP, KUR, LQB, HEV, NAF, SFG, HED, ExpType, Observation
import database_Handler
import glob, os
from django.apps import apps
import datetime
from Lab_Misc.models import SampleBase
from Lab_Dash.models import OCA as OCA_dash
from Lab_Dash.models import KUR as KUR_dash
from Exp_Sub.models import ExpPath as Sub_ExpPath
from Exp_Sub.models import LSP

EXP_Base_Dir = '..\\..\\..'
Sub_EXP_Base_Dir = '../../02_Experiments/02_Sub_Exp'

def conv(x):
    return x.replace(',', '.').encode()

def get_path():
    name = 'Hand edit'
    if(len(ExpPath.objects.filter(Name=name)) == 0):
        table_name = 'Databases'
        db = database_Handler.Database()
        cwd = os.getcwd()
        os.chdir('../Configure')
        db.set_db_Name('DB_mains.db')
        Header, Array = db.get_tabel(table_name)
        print(Header)
        for row in Array:
            entry = ExpPath(Abbrev = row[2], Name = row[1], Path = row[0])
            entry.save()
        os.chdir(cwd)
        print('Sample was created.')
        del db

    else:
        print('Sample was not created. Maybe change the name.')
def sample():
    name = 'test1'
    if(len(SampleBrushPNiPAAmSi.objects.filter(Name=name)) == 0):
        table_name = 'SD'
        db = database_Handler.Database()
        cwd = os.getcwd()
        os.chdir('../Configure')
        db.set_db_Name('Sampels.db')
        Header, Array = db.get_tabel(table_name)
        for row in Array:
            print(conv(row[4]))
            birth = datetime.datetime.strptime(row[2], '%Y%m%d')
            entry = SampleBrushPNiPAAmSi(Name = (table_name + '_' + str(row[0])), 
                                        Parent = row[1], Birth = birth, Length_cm = float(conv(row[4])), 
                                        Width_cm = float(conv(row[5])), Thickness_SiO2_nm = float(conv(row[8])), 
                                        Thickness_PGMA_nm = float(conv(row[9])), Thickness_PNiPAAm_nm = float(conv(row[10])), 
                                        Number_on_back = int(row[11]))
            entry.save()
            entry.Polymer.add(Polymer.objects.get(pk=1))
        os.chdir(cwd)
        print('Sample was created.')

    else:
        print('Sample was not created. Maybe change the name.')

class connect_sub():
    def LSP_OCA(self):
        for item in LSP.objects.all():
            Possible_ocas = OCA.objects.filter(Date_time__date=item.Date_time.date())
            time_diffs = []
            pks = []
            for oca in Possible_ocas:#vergleiche mit allen OCAs an diesem Tag
                time_diffs.append(abs(oca.Date_time - item.Date_time))
                pks.append(oca.id)
            pk_to_add = pks[time_diffs.index(min(time_diffs))]
            entry_add = OCA.objects.get(pk = pk_to_add)
            entry_add.Sub_Exp.add(item)


class Support_class():
    def __init__(self, row, Header):
        self.row = row
        self.Header = Header
    def get_field_float(self, field_name):
        try:
            Ind_field = self.Header.index(field_name)
            return float(self.row[Ind_field])
        except:
            return None

    def get_field(self, field_name):
        try:
            Ind_field = self.Header.index(field_name)
            return self.row[Ind_field]
        except:
            return None

class get_Sub_Exp():
    cwd = os.getcwd()
    def get_dates(self):
        all_dates =[]
        for date in glob.glob("*/"):
            try:
                is_date = datetime.datetime.strptime(date[0:-1], '%Y%m%d')
                all_dates.append(date)
            except:
                pass
        return all_dates

    def get_table_names(self, db):
        data_bases = []
        for data_base in glob.glob("*.db"):
            data_bases.append(data_base)
        db.set_db_Name(data_bases[-1])#take last table in case there are multiple
        return db.get_tabel_names()

    def LSP(self):
        LSP_path_data = Sub_ExpPath.objects.filter(Abbrev='LSP')
        LSP_path = os.path.join(Sub_EXP_Base_Dir, LSP_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(LSP_path)
        
        dates = self.get_dates()
        for date in dates:
            os.chdir(date)
            for table in glob.glob("*.xls"):
                date_time = datetime.datetime.strptime(date[0:-1] + '_' + table[0:6], '%Y%m%d_%H%M%S')
                path_to_table = os.getcwd()
                path_to_table = path_to_table[path_to_table.index('01_Experimental'):]
                path_to_table = os.path.join(path_to_table, table)
                if(True):#len(ExpBase.objects.filter(Date_time=date_time)) == 0):
                    entry = LSP(Date_time = date_time, Device = Sub_ExpPath.objects.get(Abbrev='LSP'),
                                Link_XLS = path_to_table)
                    entry.save()
                else:
                    print('data was allready loaded')
            for sample in glob.glob("*/"):
                os.chdir(sample)
                for table in glob.glob("*.xls"):
                    date_time = datetime.datetime.strptime(date[0:-1] + '_' + table[0:6], '%Y%m%d_%H%M%S')
                    path_to_table = os.getcwd()
                    path_to_table = path_to_table[path_to_table.index('01_Experimental'):]
                    path_to_table = os.path.join(path_to_table, table)
                    if(True):#len(ExpBase.objects.filter(Date_time=date_time)) == 0):
                        entry = LSP(Date_time = date_time, Device = Sub_ExpPath.objects.get(Abbrev='LSP'),
                                    Link_XLS = path_to_table)
                        entry.save()
                    else:
                        print('data was allready loaded')
                os.chdir('..')

            

            os.chdir('..')
        os.chdir(self.cwd)
        del db

class get_old_DB():
    def get_dates(self):
        all_dates =[]
        for date in glob.glob("*/"):
            try:
                is_date = datetime.datetime.strptime(date[0:-1], '%Y%m%d')
                all_dates.append(date)
            except:
                pass
        return all_dates

    def get_table_names(self, db):
        data_bases = []
        for data_base in glob.glob("*.db"):
            data_bases.append(data_base)
        db.set_db_Name(data_bases[-1])#take last table in case there are multiple
        return db.get_tabel_names()

    cwd = os.getcwd()

    def set_OCA_path(self):
        for item in OCA.objects.filter(Link_Data = ''):
            link_pdf = item.Link_PDF
            link_data = link_pdf.replace('02_Auswertung', '01_Messdaten')
            link_data = link_data.replace('pdf', 'txt')
            Folder_path = os.path.join(get_BasePath(), link_data)
            if os.path.exists(Folder_path):
                item.Link_Data = link_data
            link_vid = link_pdf.replace('02_Auswertung', '01_Messdaten')
            link_vid = link_vid.replace('pdf', 'seq')
            Folder_path = os.path.join(get_BasePath(), link_data)
            if os.path.exists(Folder_path):
                item.Link = link_vid
            item.save()

    def set_Observation(self):
        for item in ExpBase.objects.all():
            curr_entry = item
            item_id = item.id
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            curr_model = apps.get_model('Exp_Main', str(curr_exp.Abbrev))
            
            curr_item = curr_model.objects.get(id = item.id)
            try:
                types = curr_item.Temp_Buzz_word
            except:
                continue
            if not types:
                continue
            Namae_in = 'Blow'
            if types.find(Namae_in) !=-1:
                types = types.replace(Namae_in, '')
                print(types)
                entry_add = Observation.objects.get(Name = 'Unequal spreading blow')
                curr_item.Observation.add(entry_add)
                #item.Exp_type = types
                curr_item.save()

    def set_ExpType(self):
        for item in ExpBase.objects.all():
            curr_entry = item
            item_id = item.id
            curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
            curr_model = apps.get_model('Exp_Main', str(curr_exp.Abbrev))
            
            curr_item = curr_model.objects.get(id = item.id)
            try:
                types = curr_item.Temp_Buzz_word
            except:
                continue
            if not types:
                continue
            Namae_in = 'MoA'
            if types.find(Namae_in) !=-1:
                types = types.replace(Namae_in, '')
                print(types)
                entry_add = ExpType.objects.get(Name = 'Oscillating drop')
                curr_item.Type.add(entry_add)
                #item.Exp_type = types
                curr_item.save()

    def minxing_con(self):
        OCA_path_data = ExpPath.objects.filter(Abbrev='CON')
        OCA_path = os.path.join(EXP_Base_Dir, OCA_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(OCA_path)
        dates = self.get_dates()
        for date in dates:
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        Name = sup.get_field('ID:')
                        Temp_Atmosphere_relax = sup.get_field('EtOH/H$_2$O:')
                        try:
                            float(Temp_Atmosphere_relax)
                            print(Name)
                            print(Temp_Atmosphere_relax)
                            curr_entry = CON.objects.get(Name = Name)
                            curr_entry.Temp_Mixing_ratio = Temp_Atmosphere_relax
                            curr_entry.save()
                        except:
                            pass

            os.chdir('..')
        os.chdir(self.cwd)
        del db


    def OCA(self):
        OCA_path_data = ExpPath.objects.filter(Abbrev='OCA')
        OCA_path = os.path.join(EXP_Base_Dir, OCA_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(OCA_path)
        dates = self.get_dates()
        for date in dates:
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry_dash = OCA_dash(Name = 'Dash ' + sup.get_field('ID:'), CA_high_degree = sup.get_field_float('CA_high in degree'), CA_low_degree = sup.get_field_float('CA_low in degree'), 
                                                BD_high_mm = sup.get_field_float('BD_high in mm'), BD_low_mm = sup.get_field_float('BD_low in mm'), Time_high_sec = sup.get_field_float('Time_low in sec'), 
                                                Time_low_sec = sup.get_field_float('Time_high in sec'))
                            entry_dash.save()
                            entry = OCA(Date_time = date_time, Temp_Volume = sup.get_field('Volume:'), Sample_name = SampleBase.objects.get(Name=table[6:]),
                                        Device = ExpPath.objects.get(Abbrev='OCA'), Name = sup.get_field('ID:'), Temp_Observation = sup.get_field('Observation:'),
                                        Comment = sup.get_field('Comment:'), Exp_type = sup.get_field('Experiment type:'),  Temp_Hypothesis = sup.get_field('Hypothesis:'),
                                        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'), Link_Video = sup.get_field('Video:'), Link_Data = sup.get_field('Raw Data:'),
                                        Link_PDF = sup.get_field('Result PDF:'), Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),
                                        Temp_Flowrate = sup.get_field('Flowrate:'), Temp_Buzz_word = sup.get_field('Buzz Word:'), 
                                        Temp_Bath_time = sup.get_field('Bath time water:'), Dash = entry_dash)
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def HED(self):
        Abb = 'HED'
        HED_path_data = ExpPath.objects.filter(Abbrev=Abb)
        HED_path = os.path.join(EXP_Base_Dir, HED_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(HED_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = HED(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def SFG(self):
        Abb = 'SFG'
        SFG_path_data = ExpPath.objects.filter(Abbrev=Abb)
        SFG_path = os.path.join(EXP_Base_Dir, SFG_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(SFG_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = SFG(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def NAF(self):
        Abb = 'NAF'
        NAF_path_data = ExpPath.objects.filter(Abbrev=Abb)
        NAF_path = os.path.join(EXP_Base_Dir, NAF_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(NAF_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = NAF(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def HEV(self):
        Abb = 'HEV'
        HEV_path_data = ExpPath.objects.filter(Abbrev=Abb)
        HEV_path = os.path.join(EXP_Base_Dir, HEV_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(HEV_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = HEV(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def LQB(self):
        Abb = 'LQB'
        LQB_path_data = ExpPath.objects.filter(Abbrev=Abb)
        LQB_path = os.path.join(EXP_Base_Dir, LQB_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(LQB_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = LQB(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def KUR(self):
        Abb = 'KUR'
        KUR_path_data = ExpPath.objects.filter(Abbrev=Abb)
        KUR_path = os.path.join(EXP_Base_Dir, KUR_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(KUR_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry_dash = OCA_dash(Name = 'Dash ' + sup.get_field('ID:'), CA_high_degree = sup.get_field_float('CA_high in degree'), CA_low_degree = sup.get_field_float('CA_low in degree'), 
                                                BD_high_mm = sup.get_field_float('BD_high in mm'), BD_low_mm = sup.get_field_float('BD_low in mm'), Time_high_sec = sup.get_field_float('Time_low in sec'), 
                                                Time_low_sec = sup.get_field_float('Time_high in sec'))
                            entry_dash.save()
                            entry = KUR(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),    Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                    Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                  Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),          Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),              Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'),      Dash = entry_dash)
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def DIP(self):
        Abb = 'DIP'
        DIP_path_data = ExpPath.objects.filter(Abbrev=Abb)
        DIP_path = os.path.join(EXP_Base_Dir, DIP_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(DIP_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = DIP(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def NEL(self):
        Abb = 'NEL'
        NEL_path_data = ExpPath.objects.filter(Abbrev=Abb)
        NEL_path = os.path.join(EXP_Base_Dir, NEL_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(NEL_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = NEL(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def RLD(self):
        Abb = 'RLD'
        RLD_path_data = ExpPath.objects.filter(Abbrev=Abb)
        RLD_path = os.path.join(EXP_Base_Dir, RLD_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(RLD_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = RLD(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Mixing_ratio = sup.get_field('EtOH/H$_2$O:'),
                                        Temp_Atmosphere_relax = sup.get_field('Atmosphere relax time:'),   Temp_Flowrate = sup.get_field('Flowrate:'),            Temp_Volume = sup.get_field('Volume:'), 
                                        Temp_Buzz_word = sup.get_field('Buzz Word:'),                      Temp_Bath_time = sup.get_field('Bath time water:'),
                                        t1 = sup.get_field('tE1:'),                                        t2 = sup.get_field('tE2:'),                              t3 = sup.get_field('tE3:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def SEM(self):
        Abb = 'SEM'
        SEM_path_data = ExpPath.objects.filter(Abbrev=Abb)
        SEM_path = os.path.join(EXP_Base_Dir, SEM_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(SEM_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = SEM(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Buzz_word = sup.get_field('Buzz Word:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db

    def CON(self):
        Abb = 'CON'
        CON_path_data = ExpPath.objects.filter(Abbrev=Abb)
        CON_path = os.path.join(EXP_Base_Dir, CON_path_data[0].Path)
        db = database_Handler.Database()
        os.chdir(CON_path)
        dates = self.get_dates()
        for date in dates:
            print(date)
            os.chdir(date)
            tables = self.get_table_names(db)
            for table in tables:
                if table[0:6] == 'Probe_':
                    print(table[6:])
                    Header, Array = db.get_tabel(table)
                    for row in Array:
                        sup = Support_class(row, Header)
                        if(len(ExpBase.objects.filter(Name=sup.get_field('ID:'))) == 0):
                            date_time = datetime.datetime.strptime(sup.get_field('Date:') + '_' + sup.get_field('Time:'), '%Y%m%d_%H%M%S')
                            entry = CON(Name = sup.get_field('ID:'),                                       Sample_name = SampleBase.objects.get(Name=table[6:]),   Date_time = date_time,
                                        Device = ExpPath.objects.get(Abbrev=Abb),                           Comment = sup.get_field('Comment:'),                   Exp_type = sup.get_field('Experiment type:'),
                                        Link_Video = sup.get_field('Video:'),                              Link_Data = sup.get_field('Raw Data:'),                Link_PDF = sup.get_field('Result PDF:'),
                                        Temp_Observation = sup.get_field('Observation:'),                  Temp_Hypothesis = sup.get_field('Hypothesis:'),        Temp_Buzz_word = sup.get_field('Buzz Word:'),
                                        Temp_Bath_time = sup.get_field('Bath time water:'))
                            entry.save()
                        else:
                            print('data was allready loaded')
            os.chdir('..')
        os.chdir(self.cwd)
        del db
