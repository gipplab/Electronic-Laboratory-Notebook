import glob, os
import stat
import time
import datetime
from .models import ExpPath, RSD
from Lab_Misc import General
from django.db.models import Q


def get_closest_to_dt(qs, dt):
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

cwd = os.getcwd()
def Sort_CON():
    con_path = ExpPath.objects.get(Abbrev = 'CON').Path
    os.chdir(os.path.join(General.get_BasePath, con_path))

    for file in glob.glob("*.mov"):
        record_time = os.path.getmtime(file)
        record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format
        folder_name = str(record_time.strftime('%Y%m%d'))
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        os.rename(file, os.path.join(folder_name,file))

    for date in glob.glob("*/"):
        os.chdir(date)
        old_record_time = datetime.datetime(2015, 1, 1, 12, 12, 12)
        for file in glob.glob("*.mov"):
            record_time = os.path.getmtime(file)
            record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format

            if record_time - old_record_time > datetime.timedelta(minutes=1):
                folder_name = str(record_time.strftime('%H%M%S'))
                if not os.path.exists(folder_name):
                    os.makedirs(folder_name)
            os.rename(file, os.path.join(folder_name,file))
            old_record_time = record_time
        os.chdir('..')


def Sort_RSD():
    con_path = ExpPath.objects.get(Abbrev = 'RSD').Path
    os.chdir(os.path.join(General.get_BasePath, con_path))
    delay = 30
    for file in glob.glob("*.mov"):
        record_time = os.path.getmtime(file)
        record_time = datetime.datetime.fromtimestamp(record_time)
        if record_time - old_record_time < datetime.timedelta(minutes=26):
            path = os.path.join(date, time_str, drop)
            if not os.path.exists(path):
                os.makedirs(path)
            os.rename(file, os.path.join(path,file))
            old_record_time = record_time
            continue
        if record_time - old_record_time < datetime.timedelta(minutes=26+delay+1):
            i+=1
            drop = 'Drop_' + str(i)
            path = os.path.join(date, time_str, drop)
            if not os.path.exists(path):
                os.makedirs(path)
            os.rename(file, os.path.join(path,file))
            old_record_time = record_time
            continue
        if record_time - old_record_time > datetime.timedelta(minutes=26+delay):
            Exps_noVideo = RSD.objects.filter(Q(Link__isnull = True) | Q(Link__exact='')).order_by('Date_time')
            closest_entry = get_closest_to_dt(Exps_noVideo, record_time)
            delay = closest_entry.Script.delay
            date = str(record_time.strftime('%Y%m%d'))
            i = 1
            time_str = str(record_time.strftime('%H%M%S'))
            drop = 'Drop_' + str(i)
            path = os.path.join(date, time_str, drop)
            if not os.path.exists(path):
                os.makedirs(path)
            os.rename(file, os.path.join(path,file))
            old_record_time = record_time
'''
is_not_first = False
for file in glob.glob("*.mov"):
    record_time = os.path.getmtime(file)
    record_time = datetime.datetime.fromtimestamp(record_time) #convert to datetime format

    if is_not_first:
        print(record_time - old_record_time)
    is_not_first = True
    old_record_time = record_time


os.chdir(os.path.join('../01_Messdaten/', date))


if not os.path.exists(date):
    os.makedirs(date)

for probe in glob.glob("*/"):
    os.chdir(probe)

for file in glob.glob("*.txt"):
        j +=1
'''