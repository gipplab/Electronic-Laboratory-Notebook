import glob, os
import datetime
from Exp_Main.models import ExpBase, ExpPath
from Exp_Sub.models import ExpBase as ExpBase_Sub
from Exp_Sub.models import ExpPath as ExpPath_Sub
from django.apps import apps


cwd = os.getcwd()
if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
    BaseFolderName = '01_Experimental'
else:
    BaseFolderName = '01_Data'

OS_BasePath = 'Add Basepart of your local device'
def get_BasePath():
    if os.environ['DJANGO_SETTINGS_MODULE'] == 'Private.settings':
        return cwd[0:cwd.find('01_Experimental')]
    else:
        path = os.path.join(cwd, BaseFolderName)
        if os.path.exists(path):
            return '/code'
        else:
            print('Basepath not found restart program.')


def get_DatesInFolder():
    all_dates =[]
    for date in glob.glob("*/"):
        try:
            is_date = datetime.datetime.strptime(date[0:-1], '%Y%m%d')
            all_dates.append(date)
        except:
            pass
    return all_dates

def is_AppendableTime(file_name):
    try:
        is_date = datetime.datetime.strptime(file_name[0:6], '%H%M%S')
        return True
    except:
        return False

def save_index(array, item):
    try:
        index = array.index(item)
    except:
        index = -1
    return index

def get_LastIndex(list, searched):
    indices = [i for i, x in enumerate(list) if x == searched]
    return indices[-1]

def get_ModelOrigin(ModelName):
    try:
        ExpPath.objects.get(Abbrev = ModelName)
        return 'Exp_Main'
    except:
        try:
            ExpPath_Sub.objects.get(Abbrev = ModelName)
            return 'Exp_Sub'
        except:
            return None


def get_in_full_model(Main_id):
    curr_entry = ExpBase.objects.get(pk = Main_id)
    curr_exp = ExpPath.objects.get(Name = str(curr_entry.Device))
    curr_model = apps.get_model('Exp_Main', str(curr_exp.Abbrev))
    entry = curr_model.objects.get(pk = Main_id)
    return entry

def get_in_full_model_sub(Main_id):
    curr_entry = ExpBase_Sub.objects.get(pk = Main_id)
    curr_exp = ExpPath_Sub.objects.get(Name = str(curr_entry.Device))
    curr_model = apps.get_model('Exp_Sub', str(curr_exp.Abbrev))
    entry = curr_model.objects.get(pk = Main_id)
    return entry

def get_FloatAfterTrigger(string, trigger):
    """Allows to retrive number after keyword ignors first blank.
    e.g. sting = blax 4,3sdflk would return 4.3
    """
    def conv(x):
        return x.replace(',', '.').encode()
    Float = None
    if string.find(trigger)!=-1:
        if trigger == 'y':
            ind = get_LastIndex(string, trigger)
        else:
            ind = string.index(trigger)
        for i in range(8):
            try:
                Float = float(conv(string[ind+1:ind+2+i]))
            except:
                if i == 0:
                    pass
                else:
                    break
    return Float