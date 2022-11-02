from .models import ExpBase as ExpBase_Sub
from .models import ExpPath as ExpPath_Sub
from .models import Gas
from Lab_Misc.Generate import CreateAndUpdate as CreateAndUpdate_Misc
import glob, os

class CreateAndUpdate(CreateAndUpdate_Misc):
    ExpBase_curr = ExpBase_Sub
    ExpPath_curr = ExpPath_Sub
    Exp_Category = 'Exp_Sub'
    Report_folder = 'Reports_Sub'

    def ModelSpecificChanges(self, date, file, Exp, entry, sample=None):
        if Exp.Abbrev == 'MFL':
            self.add_Gas(file, entry)
            entry.save()
        if Exp.Abbrev == 'MFR':
            self.add_Gas(file, entry)
            entry.save()
        if Exp.Abbrev == 'HME':
            self.add_environment(file, entry)
            entry.save()
        if Exp.Abbrev == 'CAP':
            self.add_CAP_files(file, entry)
            entry.save()
        self.f.write('The file  ' + file + ' created the entry with the id ' + str(entry.id) + ' <br>\n')

    def add_Gas(self, file, entry):
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
        all_Gas = Gas.objects.all()
        No_gas_found = True
        for gas in all_Gas:
            try:
                file.index(gas.Name)
                entry.Gas.add(gas.id)
                self.f.write('Identify ' + str(gas.Name) + ' as Gas used. <br>\n')
                No_gas_found = False
                break
            except:
                pass
        if No_gas_found:
            self.TotalWarnings += 1
            self.f.write('<em class="text-warning">No gas was found!</em> <br>\n')

    def add_environment(self, file, entry):
        env_names = ['cell', 'room']
        env_ids = ['1', '2']
        No_gas_found = True
        for env_name, env_id in zip(env_names, env_ids):
            try:
                file.index(env_name)
                entry.Environments = env_id
                self.f.write('Identify ' + str(env_name) + ' as environment used. <br>\n')
                No_gas_found = False
                break
            except:
                pass
        if No_gas_found:
            self.TotalWarnings += 1
            self.f.write('<em class="text-warning">No environment was found!</em> <br>\n')

    def add_CAP_files(self, file, entry):
        entry.Link = self.get_FullPath(file)
        entry.Link_Video = self.get_FullPath(file)  
        self.f.write('<p>Added the file ' + file)
        for file_in_Folder in glob.glob("*.*"): # add path of data file
            if (file_in_Folder[0:6] == file[0:6]) and (file_in_Folder[-4:] == '.csv'):
                entry.Link_Data = self.get_FullPath(file_in_Folder)
                self.f.write(', add ' + file_in_Folder + '. ')

        # try to add additional experiment details from file name
        try:
            ind_end = file.find('fps')
            ind_start = ind_end - (file[:ind_end][::-1]).find('_')
            entry.FPS = float(file[ind_start:ind_end])
        except:
            pass
        try:
            ind_start = file.find('_K') + 2
            ind_end = ind_start + (file[ind_start:]).find('_')
            try:
                entry.Capillary = int(file[ind_start:ind_end])
            except:
                entry.Capillary = int(file[ind_start:ind_end-1])
        except:
            pass
        