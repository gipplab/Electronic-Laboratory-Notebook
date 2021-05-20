from Exp_Sub.models import ExpBase
from Exp_Sub.models import ExpPath as ExpPath_sub
from Exp_Main.models import ExpBase as Main_ExpBase
from Lab_Dash.models import GRP as GRP_dash
from Exp_Main.models import Group as Group_Model
import pytz
from django.db.models import Q
from Lab_Misc.General import *
from django.apps import apps
from Lab_Misc.models import SampleBase
import datetime
import glob, os
from django.utils import timezone

class CreateAndUpdate():
    ExpPath_curr = ExpPath_sub
    ExpBase_curr = ExpBase
    Exp_Category = 'Exp_Sub'
    Report_folder = 'Reports_Sub'

    if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
        Reports_path = "Private/Reports/"
    else:
        Reports_path = "Lab_Misc/templates/"

    def is_ValidFile(self, file, Exp):
        """
        is_ValidFile checks if file is valid

        Checks if file has a time in the beginning of the filename and if the file ending matches to the allowed endings

        Parameters
        ----------
        file : string
            name of the current file
        Exp : Model
            Model in ExpPath

        Returns
        -------
        Bool
            whether the file is valid or not
        """        
        if not is_AppendableTime(file):
            self.TotalErrors += 1
            self.f.write('<p class="text-danger">Error!<br>')
            self.f.write('The file ' + file + ' can not be added! Consider renaming or moving the file.</p>\n')
        else:
            start_i = get_LastIndex(file, '.')
            correct_ending = False
            for ending in Exp.File_ending.all():
                if file[start_i+1:] == ending.Ending:
                    correct_ending = True
            if correct_ending:
                return True
            else:
                self.TotalWarnings += 1
                allowed_endings = [str(ending.Ending) for ending in Exp.File_ending.all()]
                self.f.write('<em class="text-warning">The file ' + file + ' has none of the following allowed endings: ' + ', '.join(allowed_endings) + '; thus will be ignored!</em> <br>\n')

    def get_NewerDates(self, days, Exp):
        """
        get_NewerDates gets folders names that are newer than a certain date

        gets folders that are newer than a certain date

        Parameters
        ----------
        days : int
            days that should be gone back from latest entry. These folders that come in to that range will be added to the list
        Exp : Model
            Model in ExpPath

        Returns
        -------
        list
            List of all the date that meet the criteria
        """
        #latest_Exp = self.get_LatestExp(Exp)
        latest_Exp = datetime.datetime.now()#search backwards from today
        folder_start = latest_Exp - datetime.timedelta(days=days)
        folder_start = folder_start.date()
        os.chdir(os.path.join(get_BasePath(), Exp.Path))
        dates = get_DatesInFolder()
        NewerDates = []
        for date in dates:
            curr_date = datetime.datetime.strptime(date[:-1], '%Y%m%d')
            curr_date = curr_date.date()
            if curr_date-folder_start < datetime.timedelta(days=0):
                pass
            else:
                NewerDates.append(date)
        if len(NewerDates) == 0:
            self.TotalWarnings += 1
            self.f.write('<em class="text-warning">There are no folders older than ' + folder_start.strftime('%Y%m%d') + ' for ' + Exp.Name + '.</em> <br>\n')
        return NewerDates
    
    def get_FilesInCurrFolder(self):
        files = []
        for File in glob.glob("*.*"):
            files.append(File)
        return files

    def get_FullPath(self, file):
        """
        get_FullPath retruns path of the file

        retruns path of the file until '01_Experimental' by connecting file name and the current directory

        Parameters
        ----------
        file : string
            name of the current file

        Returns
        -------
        string
            path of the file
        """        
        path_to_file = os.getcwd()
        path_to_file = path_to_file[path_to_file.index(BaseFolderName):]
        path_to_file = os.path.join(path_to_file, file)
        return path_to_file
    
    def get_DateOfFile(self, date, file):
        """
        get_DateOfFile retruns date and time in date time format

        retruns date and time in date time format with the timezone of django

        Parameters
        ----------
        date : string
            Folder name in form of a date with the format %Y%m%d
        file : string
            Name of the file with time in the front with the format %H%M%S

        Returns
        -------
        datetime
            datetime of file
        """        
        date_of_file = datetime.datetime.strptime(date[0:-1] + '_' + file[0:6], '%Y%m%d_%H%M%S')
        date_of_file = date_of_file.astimezone(timezone.get_current_timezone())
        return date_of_file

    def is_OlderLatestEXP(self, file, Exp, date):
        """
        is_OlderLatestEXP Checks is file is older than the latest entry

        Checks is file is older than the latest entry and if so return true

        Parameters
        ----------
        file : string
            Name of the file
        Exp : Model
            Model in ExpPath
        date : [type]
            [description]

        Returns
        -------
        Bool
            Whether the file is older than the latest entry
        """        
        date_of_file = self.get_DateOfFile(date, file)
        latest_Exp = self.get_LatestExp(Exp)
        if date_of_file-latest_Exp.Date_time <= datetime.timedelta(days=0):
            path_to_file = self.get_FullPath(file)
            self.TotalWarnings += 1
            self.f.write('<em class="text-warning">The path ' + path_to_file + ' has not been found in ' + Exp.Name + ', try finding existing Entry for path.</em> <br>\n')
            return False
        else:
            return True

    def get_closest_to_dt(self, qs, dt):
        """
        get_closest_to_dt Gets closet entry to given datetime

        Gets closet entry to given datetime and retruns the closeset entry

        Parameters
        ----------
        qs : [type]
            query sting
        dt : datetime
            a chosen datetime

        Returns
        -------
        [type]
            The entry that is closest to the datetime
        """
        greater = qs.filter(Date_time__gte=dt).order_by("Date_time").first()
        less = qs.filter(Date_time__lte=dt).order_by("-Date_time").first()

        if greater and less:
            return greater if abs(greater.Date_time - dt) < abs(less.Date_time - dt) else less
        else:
            return greater or less
    
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
        latest_Exp = model.objects.filter(Link__isnull = False).order_by('-Date_time')[0]#latest entry with link
        return latest_Exp

    def Success_AddExistingPath(self, date, file, Exp):
        """
        Success_AddExistingPath Tries to add a path to an existing entry

        Tries to add a path to an existing entry if success full retruns true if not false

        Parameters
        ----------
        date : string
            Folder name in form of a date with the format %Y%m%d
        file : string
            Name of the file
        Exp : Model
            Model in ExpPath

        Returns
        -------
        Bool
            True or false whether the path could be added to an entry
        """
        path_to_file = self.get_FullPath(file)
        date_of_file = self.get_DateOfFile(date, file)
        model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
        empty_entry = model.objects.filter(Q(Link = '') | Q(Link__isnull=True))
        if empty_entry.count() == 0:
            return False
        else:
            closest_entry = self.get_closest_to_dt(empty_entry, date_of_file)
            if abs(closest_entry.Date_time - date_of_file) <= datetime.timedelta(minutes=5):#Time difference between entry and file is smaller than 5 minutes
                closest_entry.Link = path_to_file
                closest_entry.save()
                self.f.write('The path ' + path_to_file + ' was added to ' + str(closest_entry.Name) + '. <br>\n')
                return True
            else:
                return False

    def get_SampleName(self, FolderName):
        """
        get_SampleName Tries to extract the sample Name out of the Folder Name

        Tries to extract the sample Name out of the Folder Name

        Parameters
        ----------
        FolderName : string
            Name of folder which contains the name of the sample

        Returns
        -------
        string
            None / name of the sample
        """        
        if FolderName == None:
            SampleName = None
        elif FolderName.find('Probe_') == -1:
            try:
                SampleName = FolderName[:5]
                SampleBase.objects.get(Name=FolderName[:5])
            except:
                SampleName = None
        else:
            try:
                SampleName = FolderName[6:11]
                SampleBase.objects.get(Name=FolderName[6:11])
            except:
                SampleName = None
        if SampleName == None:
            self.TotalErrors += 1
            self.f.write('<p class="text-danger">Error!<br>')
            self.f.write('For the folder ' + str(FolderName) + ' no sample in the sample database was found.</p>\n')
        return SampleName

    def Add_EntryToDB(self, date, file, Exp, sample=None, Group=None):
        """
        Add_EntryToDB adds an entry to the database

        Adds an entry with its path to the database.

        Parameters
        ----------
        date : string
            Folder name in form of a date with the format %Y%m%d
        file : string
            Name of the file with time in the front with the format %H%M%S
        Exp : Model
            Model in ExpPath
        """
        entries_added = False
        date_time = datetime.datetime.strptime(date[0:-1] + '_' + file[0:6], '%Y%m%d_%H%M%S')
        path_to_file = self.get_FullPath(file)
        model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
        if sample == None:
            entry = model(Date_time = date_time, Device = self.ExpPath_curr.objects.get(Abbrev=str(Exp.Abbrev)),
                        Link = path_to_file)
            entries_added = True
        else:
            SampleName = self.get_SampleName(sample)
            if SampleName == None:
                pass
            else:
                entry = model(Date_time = date_time, Device = self.ExpPath_curr.objects.get(Abbrev=str(Exp.Abbrev)),
                                Sample_name = SampleBase.objects.get(Name=SampleName))
                entries_added = True
        if entries_added:
            self.entries_added = True
            entry.save()
            self.f.write('The file  ' + file + ' created the entry with the id ' + str(entry.id) + ' <br>\n')
            self.entries_added = True
            self.ModelSpecificChanges(date, file, Exp, entry, sample)
        if not Group == None:
            Group.ExpBase.add(entry.id)
            entry_dash = GRP_dash()
            entry_dash.save()
            Group.Dash = entry_dash
            Group.save()

    def ModelSpecificChanges(self, date, file, Exp, entry, sample=None):
        pass

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
        model = apps.get_model(self.Exp_Category, str(Exp.Abbrev))
        path_to_file = self.get_FullPath(file)
        if model.objects.all().count() == 0:#if there are no entries
            self.Add_EntryToDB(date, file, Exp, Group)
        if model.objects.filter(Link = path_to_file).count() == 0:#if path is not found in model
            if self.is_ValidFile(file, Exp):
                latest_Exp = self.get_LatestExp(Exp)
                if self.is_OlderLatestEXP(file, Exp, date):
                    self.Add_EntryToDB(date, file, Exp, Group)
                else:
                    if self.Success_AddExistingPath(date, file, Exp):
                        pass
                    else:
                        self.Add_EntryToDB(date, file, Exp, Group)

    def ManageEntriesForFiles(self, date, Exp, sample=None, Group=None):
        """
        CreateEntryForFiles Iterates all files and adds them to the DB

        Iterates all files and adds them to the DB. Also prints some lines

        Parameters
        ----------
        date : string
            Folder name in form of a date with the format %Y%m%d
        Exp : Model
            Model in ExpPath
        """        
        if sample==None:
            self.f.write('<li>Search in ' + date + '</li>\n')
            self.f.write('<ul>')
        else:
            self.f.write('<li>Search in ' + date + sample + '</li>\n')
            if Exp.Abbrev == 'RSD':
                file = None
                self.manage_Path(Exp, date, file, sample, Group)
        self.f.write('<p>')
        for file in glob.glob("*.*"):
            self.manage_Path(Exp, date, file, sample, Group)
        self.f.write('</p>')

    def Generate_Entries(self):
        def handle_dates():
            for date in dates:
                os.chdir(date)
                self.ManageEntriesForFiles(date, Exp)
                for sample in glob.glob("*/"):
                    os.chdir(sample)
                    self.ManageEntriesForFiles(date, Exp, sample)
                    for Group in glob.glob("*/"):
                        os.chdir(Group)
                        GroupEntry = self.ManageGroup(date, Exp, sample, Group)
                        for SubGroup in glob.glob("*/"):
                            os.chdir(SubGroup)
                            SubGroupEntry = self.ManageGroup(date, Exp, sample, GroupEntry, SubGroup)
                            for SubSubGroup in glob.glob("*/"):
                                os.chdir(SubSubGroup)
                                self.ManageGroup(date, Exp, sample, GroupEntry, SubGroupEntry, SubSubGroup)
                                os.chdir('..')
                            os.chdir('..')
                        os.chdir('..')
                    os.chdir('..')
                os.chdir('..')
                self.f.write('</ul>')
            self.f.write('</ul>')
        self.entries_added = False
        self.TotalErrors = 0
        self.TotalWarnings = 0

        cwd = os.getcwd()
        Path_to_report = self.Reports_path + self.Report_folder + "/Generated_entries_" + datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S") + ".html"
        self.f= open(Path_to_report,"w+")
        Exp_Path = self.ExpPath_curr.objects.all()
        for Exp in Exp_Path:
            if self.ExpBase_curr.objects.filter(Device = Exp.id).count() == 0:#If no entries exist
                self.f.write('<br>\n')
                self.f.write('<p>No entries for ' + Exp.Name + ' have been found!</p>\n')
                self.f.write('<p>Search all folders in ' + Exp.Path + '</p>\n')
                self.f.write('<ul>')
                os.chdir(os.path.join(get_BasePath(), Exp.Path))
                dates = get_DatesInFolder()
                handle_dates()
            else:
                self.f.write('<br>\n')
                self.f.write('<p>Entries for ' + Exp.Name + ' have been found!</p>\n')
                dates = self.get_NewerDates(15, Exp)
                if len(dates) == 0:
                    pass
                else:
                    self.f.write('<p>Search all folders that are newer or equal to ' + dates[0][0:-1] + '</p>\n')
                self.f.write('<ul>')
                handle_dates()

        os.chdir(cwd)
        self.f.write('</div>\n{% endblock content %}')
        self.f.close
        self.f= open(Path_to_report,"r")
        data = self.f.read()
        self.f.close
        self.f= open(Path_to_report,"w")
        data = self.f.write('{% extends "base.html" %}\n{% block content %}' + '<div class="Report">\n<style>\n    .Report\n    p{text-align: left;}\n</style>' + "<h3>Generate entries</h3><br>\n A total of " + str(self.TotalErrors) + " errors and a total of " + str(self.TotalWarnings) + " warnings where found!<br>\n" + data)
        self.f.close
        if (self.TotalErrors == 0) & (self.entries_added):
            Report_Names = self.Generate_Names()
            return Path_to_report, Report_Names
        else:
            return [Path_to_report]

    def ManageGroup(self, date, Exp, sample, Group, SubGroup = None, SubSubGroup = None):
        if SubSubGroup == None:
            if SubGroup == None:
                if Group[0:3] == 'GRP':
                    group_entry = Group_Model()
                    group_entry.Description = Group
                    group_entry.save()
                    self.ManageEntriesForFiles(date, Exp, sample, group_entry)
                    return group_entry
            elif SubGroup[0:3] == 'GRP':
                id = Group.id
                sub_group_entry = Group_Model(parent = Group_Model.objects.get(pk=id))
                sub_group_entry.Description = SubGroup
                sub_group_entry.save()
                self.ManageEntriesForFiles(date, Exp, sample, sub_group_entry)
                return sub_group_entry
        elif SubSubGroup[0:3] == 'GRP':
            id = SubGroup.id
            Sub_sub_group_entry = Group_Model(parent = Group_Model.objects.get(pk=id))
            Sub_sub_group_entry.Description = SubSubGroup
            Sub_sub_group_entry.save()
            self.ManageEntriesForFiles(date, Exp, sample, Sub_sub_group_entry)
            return Sub_sub_group_entry



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
                if self.ExpBase_curr.objects.filter(Name__contains = Exp.Abbrev, Device = Exp.id).count() == 0:
                    i = 0
                else:
                    Named_exps = self.ExpBase_curr.objects.filter(Name__contains = Exp.Abbrev, Device = Exp.id)
                    numbers = []
                    for item in Named_exps:
                        Name = item.Name
                        number = Name[Name.index('_')+1:]
                        numbers.append(int(number))
                        i = max(numbers)
                f.write('<p>Start number is ' + str(i+1) + '.</p>\n')
                for item in Unnamed_Exps:
                    i += 1
                    item.Name = Exp.Abbrev + '_' + str(i)
                    item.save()
                    f.write('<li>Named entry with id = ' + str(item.id) + ' ' + item.Name + '.</li>\n')

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

    def ConnectFilesToExpMain(self):
        def get_closest(model_name):
            model = apps.get_model('Exp_Main', model_name)
            return self.get_closest_to_dt(model.objects.all(), time_of_sub)
        def get_Mains_related_sub():
            model_names = []
            for f in ExpBase._meta.get_fields():
                try:
                    model = apps.get_model('Exp_Main', f.name)
                except:
                    continue
                if model.objects.all().count()>0:#if there are some entries
                    model_names.append(f.name)
            return model_names
        Path_to_report = self.Reports_path + self.Report_folder + "/Connected_entries_" + datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S") + ".html"
        f= open(Path_to_report,"w+")
        Exp_Path = ExpPath_sub.objects.all()
        for Exp in Exp_Path:
            f.write('<p>Search for unlinked experiments in ' + Exp.Name + '.</p>\n')
            f.write('<ul>')
            model = apps.get_model('Exp_Sub', str(Exp.Abbrev))
            if model.objects.all().count()>0:#if there are some entries
                Unconnected_entries = model.objects.filter(oca__isnull = True, sel__isnull = True)
                for Unconnected_entry in Unconnected_entries:
                    time_of_sub = Unconnected_entry.Date_time
                    closest_entries = []
                    for model_name in get_Mains_related_sub():
                        try:
                            model = apps.get_model('Exp_Main', model_name)
                            model.expbase_ptr
                            model.Sub_Exp
                            closest_entries.append(get_closest(model_name))
                        except:
                            pass
                    lowest_time = datetime.timedelta(minutes=5)
                    closest_entry = None
                    for entry in closest_entries:
                        if abs(entry.Date_time - time_of_sub) <= lowest_time:
                            closest_entry = entry
                    if closest_entry == None:
                        f.write('<p>The sub experiment ' + Unconnected_entry.Name + ' could not be connected to any experiments.</p>\n')
                    else:
                        closest_entry.Sub_Exp.add(Unconnected_entry.id)
                        closest_entry.save()
                        f.write('<li>The sub experiment ' + Unconnected_entry.Name + ' recorded at ' + Unconnected_entry.Date_time.strftime("%Y_%m_%d-%H_%M_%S") +  ' was connected to ' + closest_entry.Name + ' recorded at ' + closest_entry.Date_time.strftime("%Y_%m_%d-%H_%M_%S") + '.</li>\n')

            else:
                f.write('<p>There are no entries in ' + Exp.Name + '.</p>\n')
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