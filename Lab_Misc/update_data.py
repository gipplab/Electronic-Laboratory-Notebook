from .models import SampleBrushPNiPAAmSi, Polymer
import database_Handler
import glob, os
import datetime

def conv(x):
    return x.replace(',', '.').encode()

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
