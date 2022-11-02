from .models import ExpBase as ExpBase_Main, Liquid
from .models import ExpPath as ExpPath_Main
from Lab_Dash.models import SEL as SEL_dash
from Lab_Dash.models import OCA as OCA_dash
from Lab_Dash.models import LMP as LMP_dash
from Lab_Dash.models import RSD as RSD_dash
from Lab_Dash.models import SFG as SFG_dash
from Lab_Dash.models import DAF as DAF_dash
from Exp_Main.models import Group as Group_Model
from Lab_Misc.Generate import CreateAndUpdate as CreateAndUpdate_Misc
import pytz
from django.db.models import Q
from Lab_Misc.General import *
from django.apps import apps
import datetime
import glob, os
from django.utils import timezone
import numpy as np


class CreateAndUpdate(CreateAndUpdate_Misc):
    ExpBase_curr = ExpBase_Main
    ExpPath_curr = ExpPath_Main
    Exp_Category = 'Exp_Main'
    Report_folder = 'Reports'
    if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
        Reports_path = "Private/Reports/"
    else:
        Reports_path = "Lab_Misc/templates/"

    def get_LatestExp(self, Exp):
        """
        get_LatestExp Gets latest entry without a link

        Gets latest entry without a link

        Parameters
        ----------
        Exp : Model
            Model in ExpPath

        Returns
        -------
        Model entry
            latest entry without a link
        """
        model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
        latest_Exp = model.objects.all().order_by('-Date_time')[0]#latest entry with link
        return latest_Exp

    def manage_Path(self, Exp, date, file, sample=None, Group=None):
        """
        manage_Path connects path to database

        Checks if path is already used by another model. If not it is tried to connect to existing entry. If that is also not possible a new entry is created

        Parameters
        ----------
        Exp : Model
            Model in ExpPath
        date : string
            Folder name in form of a date with the format %Y%m%d
        file : string
            Name of the file with time in the front with the format %H%M%S
        """
        if is_AppendableTime(sample):
            if (str(Exp.Abbrev) == 'RLD') | (str(Exp.Abbrev) == 'CON') | (str(Exp.Abbrev) == 'SLD') | (str(Exp.Abbrev) == 'LPT'):
                model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
                Exps_noVideo = model.objects.filter(Q(Link__isnull = True) | Q(Link__exact='')).order_by('Date_time')
                date_time = self.get_DateOfFile(date, sample)
                closest_entry = self.get_closest_to_dt(Exps_noVideo, date_time)
                if abs(closest_entry.Date_time-date_time) < datetime.timedelta(minutes=5):
                    path_to_vids = self.get_FullPath(file)
                    path_to_vids = path_to_vids[:get_LastIndex(path_to_vids, '/')]
                    closest_entry.Link = path_to_vids
                    closest_entry.save()
                    self.f.write('The path ' + path_to_vids + ' was added to ' + str(closest_entry.Name) + '. <br>\n')
            elif (str(Exp.Abbrev) == 'RSD'):
                model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
                Exps_noVideo = model.objects.filter(Q(Link__isnull = True) | Q(Link__exact='')).order_by('Date_time')
                date_time = self.get_DateOfFile(date, sample)
                try:
                    closest_entry = self.get_closest_to_dt(Exps_noVideo, date_time)
                    if abs(closest_entry.Date_time-date_time) < datetime.timedelta(minutes=5+closest_entry.Script.delay):
                        path_to_vids = self.get_FullPath(sample)
                        path_to_vids = path_to_vids[:get_LastIndex(path_to_vids[:-3], '/')]
                        closest_entry.Link = path_to_vids
                        closest_entry.save()
                        self.f.write('The path ' + path_to_vids + ' was added to ' + str(closest_entry.Name) + '. <br>\n')
                        self.add_RSD_files(closest_entry)
                except:
                    self.TotalErrors += 1
                    self.f.write('<p class="text-danger">Error!<br>')
                    self.f.write('Someting did not work.</p>\n')
            elif (str(Exp.Abbrev) == 'LMP'):
                model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
                Exps_all = model.objects.all().order_by('Date_time')
                date_time = self.get_DateOfFile(date, sample)
                closest_entry = self.get_closest_to_dt(Exps_all, date_time)
                if abs(closest_entry.Date_time-date_time) > datetime.timedelta(seconds=1):
                    file = sample
                    sample = 'Allg'
                    self.Add_EntryToDB(date, file, Exp, sample, Group)
        else:
            SampleName = self.get_SampleName(sample)
            if SampleName == None:
                pass
            else:
                if str(Exp.Abbrev) == 'SFG':
                    file = self.give_file_times(file)
                model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
                if model.objects.all().count() == 0:#if there are no entries
                    self.Add_EntryToDB(date, file, Exp, sample, Group)
                path_to_file = self.get_FullPath(file)
                if model.objects.filter(Link = path_to_file).count() == 0:#if path is not found in model
                    if str(Exp.Abbrev) == 'DAF':
                        if (model.objects.filter(Link_Data = path_to_file).count() != 0) or (model.objects.filter(Link_Data_2nd_Camera = path_to_file).count() != 0) or (model.objects.filter(Link_Additional_Data_CAL = path_to_file).count() != 0) or (model.objects.filter(Link_Additional_Data_CAR = path_to_file).count() != 0) or (model.objects.filter(Link_Video = path_to_file).count() != 0) or (model.objects.filter(Link_Video_2nd_Camera = path_to_file).count() != 0):
                            # (file[len(file)-file[::-1].find(".")-3:len(file)-file[::-1].find(".")-1] == '_2')
                            return
                    if self.is_ValidFile(file, Exp, Group):
                        latest_Exp = self.get_LatestExp(Exp)
                        if self.is_OlderLatestEXP(file, Exp, date):#if experiment is newer than existing experiments
                            self.Add_EntryToDB(date, file, Exp, sample, Group)
                        else:
                            if self.Success_AddExistingPath(date, file, Exp):
                                pass
                            else:
                                self.Add_EntryToDB(date, file, Exp, sample, Group)
    
    def give_file_times(self, file):
        if is_AppendableTime(file):
            pass
            return file
        else:
            curr_path = os.getcwd()
            record_time = os.path.getmtime(file)
            record_time = datetime.datetime.fromtimestamp(record_time)
            record_time = str(record_time.strftime('%H%M%S'))
            old_path = os.path.join(curr_path, file)
            new_file = record_time + '_' + file
            new_path = os.path.join(curr_path, new_file)
            os.rename(old_path, new_path)
            return new_file

    def is_ValidFile(self, file, Exp, Group=None):
        if str(Exp.Abbrev) == 'SFG':
            if file[-11:] == '_3500.0.txt':
                return super(CreateAndUpdate, self).is_ValidFile(file, Exp)
            elif file[-9:] == '_data.txt':
                return super(CreateAndUpdate, self).is_ValidFile(file, Exp)
            elif Group != None:
                if file.find('3500.0') != -1:
                    return super(CreateAndUpdate, self).is_ValidFile(file, Exp)
            else:
                return False
        elif str(Exp.Abbrev) == 'DAF':
            if (file[-6:-4] == '_2') or (file[-6:-4] == '_P'):
                return False
            else:
                return super(CreateAndUpdate, self).is_ValidFile(file, Exp)
        else:
            return super(CreateAndUpdate, self).is_ValidFile(file, Exp)

    def ModelSpecificChanges(self, date, file, Exp, entry, sample=None):
        if Exp.Abbrev == 'SEL':
            self.add_SEL_files(file, entry)
            entry.save()
        if Exp.Abbrev == 'OCA':
            self.add_OCA_files(file, entry)
            entry.save()
        if Exp.Abbrev == 'SFG':
            self.add_SFG_files(file, entry)
            entry.save()
        if Exp.Abbrev == 'LMP':
            self.add_LMP_files(file, entry)
            entry.save()
        if Exp.Abbrev == 'DAF':
            self.add_DAF_files(file, entry)
            entry.save()
        
    def add_SFG_files(self, file, entry):
        """
        add_Gas Adds the correct gas to the entry

        Looks in the file name for gases. If a gas is found it is added to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        path = self.get_FullPath(file)
        if file.find('fake')==-1:
            if file[-9:] == '_data.txt':
                file_name = file
            else:
                file_name = file[7:-3] + '_data.txt'
            files = self.get_FilesInCurrFolder()
            ind_file = [i for i, s in enumerate(files) if file_name in s]
            if len(ind_file) ==1:
                data_file = files[ind_file[0]]
                path = self.get_FullPath(data_file)
        if os.path.isfile(os.path.join(get_BasePath(), path)):
            entry.Link = path
            self.f.write('<p>Added the file ' + path + ' to ' + str(entry.Name))
        else:
            self.f.write('<p>No path found')
        try:
            ind_1sp = file.find(' ')
            ind_1sp = ind_1sp + 1
            ind_2sp = file[ind_1sp:].find(' ')
            ind_2sp = ind_2sp + ind_1sp + 1
            ind_1_ = file[ind_2sp:].find('_')
            ind_1_ = ind_1_ + ind_2sp + 1
            Xpos = file[ind_1sp:ind_2sp-1]
            Ypos = file[ind_2sp:ind_1_-1]
            entry.XPos_mm = float(Xpos)
            entry.YPos_mm = float(Ypos)
            self.f.write(', and the x, y-position ' + Xpos + ', ' + Ypos + ' to ' + str(entry.Name))
        except:
            try:
                searched = '_'
                indices = [i for i, x in enumerate(file) if x == searched]
                Xpos = file[indices[3]+1:indices[4]]
                Ypos = file[indices[4]+1:indices[5]]
                entry.XPos_mm = float(Xpos)
                entry.YPos_mm = float(Ypos)
                self.f.write(', and the x, y-position ' + Xpos + ', ' + Ypos + ' to ' + str(entry.Name))
            except:
                pass
        if file.find('ppp')!=-1:
            entry.Polarization = '1'
        if file.find('ssp')!=-1:
            entry.Polarization = '2'
        XPos = get_FloatAfterTrigger(file, 'x')
        entry.XPos_mm = XPos
        YPos = get_FloatAfterTrigger(file, 'y')
        entry.YPos_mm = YPos
        entry.Measurement_Mode = '1'
        entry_dash = SFG_dash()
        entry_dash.save()
        entry.Dash = entry_dash
        self.f.write(' and add dash.</p>\n')

    def add_OCA_files(self, file, entry):
        """
        add_Gas Adds the correct gas to the entry

        Looks in the file name for gases. If a gas is found it is added to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        entry.Link = self.get_FullPath(file)
        self.f.write('<p>Added the file ' + file + ' to ' + str(entry.Name))
        for file_in_Folder in glob.glob("*.*"):
            if (file_in_Folder[0:6] == file[0:6]) & (file_in_Folder[file_in_Folder.find('.'):]=='.txt'):
                entry.Link_Data = self.get_FullPath(file_in_Folder)
                self.f.write(', add ' + file_in_Folder)
        entry_dash = OCA_dash()
        entry_dash.save()
        entry.Dash = entry_dash
        self.f.write(' and add dash.</p>\n')

    def add_LMP_files(self, file, entry):
        """
        add_Gas Adds the correct gas to the entry

        Looks in the file name for gases. If a gas is found it is added to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        index_link = (len(file)+1)*(-1)
        link = self.get_FullPath(file)[:index_link]
        entry.Link = link
        self.f.write('<p>Added the file ' + file + ' to ' + str(entry.Name))
        for file_in_Folder in glob.glob("*.*"):
            if (file_in_Folder[0:6] == file[0:6]) & (file_in_Folder[file_in_Folder.find('.'):]=='.txt'):
                entry.Link_Data = self.get_FullPath(file_in_Folder)
                self.f.write(', add ' + file_in_Folder)
        entry_dash = LMP_dash()
        entry_dash.save()
        entry.Dash = entry_dash
        self.f.write(' and add dash.</p>\n')
        entry.Comment = file[6:-1]

    def add_RSD_files(self, entry):
        """
        add_Gas Adds the correct gas to the entry

        Looks in the file name for gases. If a gas is found it is added to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        entry_dash = RSD_dash()
        entry_dash.save()
        entry.Dash = entry_dash
        self.f.write(' and add dash.</p>\n')
        entry.save()

    def add_SEL_files(self, file, entry):
        """
        add_Gas Adds the correct gas to the entry

        Looks in the file name for gases. If a gas is found it is added to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        entry.Link = self.get_FullPath(file)
        self.f.write('<p>Added the file ' + file + ' to ' + str(entry.Name) + '.</p>\n')
        for file_in_Folder in glob.glob("*.*"):
            if (file_in_Folder[0:6] == file[0:6]) & (file_in_Folder[file_in_Folder.find('.'):]=='.xlsx'):
                entry.Link_XLSX = self.get_FullPath(file_in_Folder)
        entry_dash = SEL_dash(Start_datetime_elli = entry.Date_time)
        entry_dash.save()
        entry.Dash = entry_dash
    
    def add_DAF_files(self, file, entry):
        """
        Looks in the file name for additional information and adds them to the entry
        Looks for additional files with similar beginning of file name and adds them to the entry

        Parameters
        ----------
        file : string
            filename with possible infomation about the gas used
        entry : [type]
            entry to which the file was added
        """
        entry.Link = self.get_FullPath(file)
        entry.Link_Video = self.get_FullPath(file)  
        self.f.write('<p>Added the file ' + file + ' to ' + str(entry.Name))
        for file_in_Folder in glob.glob("*.*"): # add paths of other files corresponding to experiment
            if file_in_Folder[0:6] == file[0:6]:
                valid_file = True
                ind = len(file_in_Folder) - file_in_Folder[::-1].find(".") - 1
                if file_in_Folder[ind:] == '.xlsx': # data file
                    if file_in_Folder[ind-7:] == '_Result.xlsx':
                        entry.Link_Result = self.get_FullPath(file_in_Folder)
                    elif file_in_Folder[ind-2:] == '_P.xlsx':
                        entry.Link_Data_2nd_Camera = self.get_FullPath(file_in_Folder)
                    elif file_in_Folder[ind-4:ind] == '_CAL':
                        entry.Link_Additional_Data_CAL = self.get_FullPath(file_in_Folder)
                    elif file_in_Folder[ind-4:ind] == '_CAR':
                        entry.Link_Additional_Data_CAR = self.get_FullPath(file_in_Folder)
                    elif file_in_Folder[ind-2] != '_':
                        entry.Link_Data = self.get_FullPath(file_in_Folder)
                    else:
                        valid_file = False
                elif (file_in_Folder[ind:] == '.MOV') or (file_in_Folder[ind:] == '.MP4'): # additional video file
                    if (file_in_Folder[ind-2:ind] == '_P') or (file_in_Folder[ind-4:ind] == '_P_1'):
                        entry.Link_Video_2nd_Camera = self.get_FullPath(file_in_Folder)
                    else:
                        valid_file = False
                if valid_file:
                    self.f.write(', add ' + file_in_Folder)

        # try to add additional experiment details from file name
        try:
            ind_end = file.find('muL')
            ind_start = ind_end - (file[:ind_end][::-1]).find('_')
            entry.Drop_Volume_muL = float(file[ind_start:ind_end])
            ind_end = ind_start - 1
            ind_start = ind_end - (file[:ind_end][::-1]).find('_')
            entry.Liquid = file[ind_start:ind_end]
        except:
            pass
        try:
            ind_end = file.find('UPM')
            ind_start = ind_end - (file[:ind_end][::-1]).find('_')
            entry.Rotations_per_min = float(file[ind_start:ind_end])
        except:
            pass
        try:
            ind_end = file.find('mm')
            ind_start = ind_end - (file[:ind_end][::-1]).find('_')
            entry.Trajectory_Radius_mm = float(file[ind_start:ind_end])
        except:
            pass
        try:
            entry.Velocity_mu_m_per_s = round(2*np.pi*entry.Trajectory_Radius_mm*1000 * entry.Rotations_per_min/60, 2)
        except:
            pass
        try:
            ind_start = len(file) - file[::-1].find("H_")
            try:
                ind_end = ind_start + (file[ind_start:]).find('_')
                entry.Height_Glass_Plate_mm = float(file[ind_start:ind_end])/200
            except:
                ind_end = ind_start + (file[ind_start:]).find('.')
                entry.Height_Glass_Plate_mm = float(file[ind_start:ind_end])/200
        except:
            pass
        try:
            ind_start = file.find('_K') + 2
            try:
                ind_end = ind_start + (file[ind_start:]).find('_')
                entry.Capillary = int(file[ind_start:ind_end])
            except:
                ind_end = ind_start + (file[ind_start:]).find('.')
                entry.Capillary = int(file[ind_start:ind_end])
        except:
            pass
        if "Ofen" in file:
            entry.Comment = "sample heated in vacuum oven"
        if "EtOH" in file:
            entry.Comment = "sample prewetted with ethanol"
        
        entry_dash = DAF_dash()
        entry_dash.save()
        entry.Dash = entry_dash
        self.f.write(' and add dash.</p>\n')

    def Generate_Names(self):
        Path_to_report = self.Reports_path + self.Report_folder + "/Named_entries_" + datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S") + ".html"
        f = open(Path_to_report,"w+")
        Exp_Path = self.ExpPath_curr.objects.all()
        for Exp in Exp_Path:
            f.write('<p>Search for unnamed experiments in ' + Exp.Name + '.</p>\n')
            f.write('<ul>')
            Unnamed_Exps = self.ExpBase_curr.objects.filter(Q(Name__isnull = True) | Q(Name__exact=''), Device = Exp.id).order_by('Date_time')
            if len(Unnamed_Exps) == 0:
                f.write('<p>No unnamed experiments in ' + Exp.Name + '.</p>\n')
            else:
                for item in Unnamed_Exps:
                    if str(Exp.Abbrev) == 'HED':
                        entries_of_sample = self.ExpBase_curr.objects.filter(Name__contains = str(item.Sample_name))
                        if entries_of_sample.count() == 0:#when this is the first entry
                            i = 0
                        else:
                            related_entry = entries_of_sample.filter(Date_time__lte=item.Date_time).order_by("-Date_time").first()
                            if related_entry == None:
                                pass
                            else:
                                Name = related_entry.Name
                                i = int(Name[Name.index('-')+1:])
                        no_name_found = True
                        f.write('<p>Start number is ' + str(i) + '.</p>\n')
                        while no_name_found:
                            i+=1
                            try:
                                item.Name = str(item.Sample_name) + '_' + Exp.Abbrev + '-' + str(i)
                                item.save()
                                f.write('<li>Named entry with id = ' + str(item.id) + ' ' + item.Name + '.</li>\n')
                                no_name_found = False
                            except:
                                pass
                    else:
                        if self.ExpBase_curr.objects.filter(Q(Name__contains = Exp.Abbrev) & Q(Name__contains = str(item.Sample_name)), Device = Exp.id).count() == 0:
                            i = 0
                        else:
                            Named_exps = self.ExpBase_curr.objects.filter(Q(Name__contains = Exp.Abbrev) & Q(Name__contains = str(item.Sample_name)), Device = Exp.id)
                            numbers = []
                            for Named_exp in Named_exps:
                                Name = Named_exp.Name
                                number = Name[Name.index('-')+1:]
                                numbers.append(int(number))
                                i = max(numbers)
                        f.write('<p>Start number is ' + str(i) + '.</p>\n')
                        if item.group_set.count() == 0:
                            uneqHun = (i % 100)
                            i = i - uneqHun
                            i += 100
                        else:
                            i += 1
                        item.Name = str(item.Sample_name) + '_' + Exp.Abbrev + '-' + str(i)
                        item.save()
                        f.write('<li>Named entry with id = ' + str(item.id) + ' ' + item.Name + '.</li>\n')
                        try:#try to find the dash model and name it
                            model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
                            item_in_model = model.objects.get(id = item.id)
                            dash_entry = item_in_model.Dash
                            dash_entry.Name = 'Dash ' + str(item.Sample_name) + '_' + Exp.Abbrev + '-' + str(i)
                            dash_entry.save()
                            f.write('<li>Named Dash entry with id = ' + str(dash_entry.id) + ' ' + dash_entry.Name + '.</li>\n')
                        except:
                            pass

            f.write('</ul>')
        f.write('<p>Search for unnamed groups.</p>\n')
        f.write('<ul>')
        Unnamed_Groups = Group_Model.objects.filter(Q(Name__isnull = True) | Q(Name__exact=''))
        if len(Unnamed_Groups) == 0:
            f.write('<p>No unnamed groups.</p>\n')
        else:
            try:
                Last_Named_Group = Group_Model.objects.filter(Name__icontains='GRP').last().Name
                number = int(Last_Named_Group[Last_Named_Group.index('-')+1:])
            except:
                number = 0
            f.write('<p>Start number is ' + str(number) + '.</p>\n')
            with Group_Model.objects.disable_mptt_updates():
                for item in Unnamed_Groups:
                    Name_str = 'GRP_'
                    ExpBase_first = item.ExpBase.first()
                    if ExpBase_first == None:
                        pass
                    else:
                        Name_str += str(ExpBase_first.Device.Abbrev)
                        Name_str += '_' + str(ExpBase_first.Sample_name) + '-'
                    print(item.get_ancestors())
                    if item.level == 0:
                        uneqHun = (number % 100)
                        number = number - uneqHun
                        number += 100
                    elif item.level == 1:
                        uneqZen = (number % 10)
                        number = number - uneqZen
                        number += 10
                    else:
                        number += 1
                    Name_str += str(number)
                    item.Name = Name_str
                    item.save()
                    expbase_grp = item.grp_set.first()
                    expbase_grp.Date_time = ExpBase_first.Date_time
                    expbase_grp.save()
                    f.write('<li>Named group with id = ' + str(item.id) + ' ' + item.Name + '.</li>\n')
                    try:#try to find the dash model and name it
                        dash_entry = item.Dash
                        dash_entry.Name = 'Dash ' + Name_str
                        dash_entry.save()
                        f.write('<li>Named Dash entry with id = ' + str(dash_entry.id) + ' ' + dash_entry.Name + '.</li>\n')
                    except:
                        pass
        f.write('</ul>')

        f.write('</div>\n{% endblock content %}')
        f.close
        f= open(Path_to_report,"r")
        data = f.read()
        f.close
        f= open(Path_to_report,"w")
        data = f.write('{% extends "base.html" %}\n{% block content %}' + '<div class="Report">\n<style>\n    .Report\n    p{text-align: left;}\n</style>' + data)
        f.close
        return Path_to_report