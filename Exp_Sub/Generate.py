from .models import ExpBase as ExpBase_Sub
from .models import ExpPath as ExpPath_Sub
from .models import Gas
from Lab_Misc.Generate import CreateAndUpdate as CreateAndUpdate_Misc

class CreateAndUpdate(CreateAndUpdate_Misc):
    ExpBase_curr = ExpBase_Sub
    ExpPath_curr = ExpPath_Sub
    Exp_Category = 'Exp_Sub'
    Report_folder = 'Reports_Sub'

    def ModelSpecificChanges(self, date, file, Exp, entry, sample=None):
        if Exp.Abbrev == 'MFL':
            self.add_Gas(file, entry)
            entry.save()
        if Exp.Abbrev == 'HME':
            self.add_environment(file, entry)
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
            bla = False
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
            bla = False
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